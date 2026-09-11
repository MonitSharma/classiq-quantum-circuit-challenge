"""Rank-constrained, space-only scheduler for the destructive XAG idea.

This module intentionally stops before QASM lowering.  A state is an affine
span of exact 4096-entry Boolean truth tables represented by resident XAG
signals.  New nonlinear signals may replace one old resident signal when the
18-dimensional rank budget is full.  Recomputing an evicted node consumes one
evaluation from the requested budget.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from md_xag import FULL, XAG, logo_truth_table, mask_indices
from destructive_xag import load_xag


ROOT = Path(__file__).resolve().parents[1]
WIRE_LIMIT = 18
INPUTS = frozenset(range(1, 13))


def _basis(values: list[int]) -> dict[int, tuple[int, int]]:
    basis: dict[int, tuple[int, int]] = {}
    for index, original in enumerate(values):
        value = original
        combination = 1 << index
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot][0]
                combination ^= basis[pivot][1]
            else:
                basis[pivot] = (value, combination)
                break
    return basis


def span_coefficients(values: list[int], target: int) -> int | None:
    """Return a coefficient mask for target in span(values), if present."""

    basis = _basis(values)
    return _reduce_with_basis(basis, target)


def _reduce_with_basis(basis: dict[int, tuple[int, int]], target: int) -> int | None:
    value = target
    combination = 0
    while value:
        pivot = value.bit_length() - 1
        if pivot not in basis:
            return None
        value ^= basis[pivot][0]
        combination ^= basis[pivot][1]
    return combination


def rank(values: list[int]) -> int:
    return len(_basis(values))


def state_basis(prepared: Prepared, resident: frozenset[int]) -> dict[int, tuple[int, int]]:
    return _basis([FULL, *(prepared.signals[signal] for signal in sorted(resident))])


@dataclass(frozen=True)
class Prepared:
    parsed: object
    graph: XAG
    signals: tuple[int, ...]
    left: tuple[int, ...]
    right: tuple[int, ...]
    nonlinear_dependencies: tuple[frozenset[int], ...]


def prepare(path: Path) -> Prepared:
    parsed = load_xag(path)
    graph = parsed.graph
    signals = tuple(graph._signals())
    left = []
    right = []
    dependencies = []
    for node in parsed.nodes:
        forms = []
        deps = set()
        for mask in (node.left_affine_mask, node.right_affine_mask):
            value = 0
            for signal in mask_indices(mask):
                value ^= FULL if signal == 0 else signals[signal]
                if signal >= 13:
                    deps.add(signal)
            forms.append(value)
        left.append(forms[0])
        right.append(forms[1])
        dependencies.append(frozenset(deps))
    return Prepared(parsed, graph, signals, tuple(left), tuple(right), tuple(dependencies))


def future_use_counts(prepared: Prepared) -> dict[int, tuple[int, ...]]:
    uses: dict[int, list[int]] = {signal: [] for signal in range(prepared.graph.signal_count)}
    for index, node in enumerate(prepared.parsed.nodes):
        node_id = 13 + index
        for mask in (node.left_affine_mask, node.right_affine_mask):
            for signal in mask_indices(mask):
                if signal:
                    uses[signal].append(node_id)
    return {signal: tuple(points) for signal, points in uses.items()}


_RANK_CACHE: dict[tuple[int, ...], int] = {}


def resident_rank(prepared: Prepared, resident: frozenset[int]) -> int:
    key = tuple(sorted(resident))
    if key not in _RANK_CACHE:
        _RANK_CACHE[key] = len(state_basis(prepared, resident))
    return _RANK_CACHE[key]


def phase_support(prepared: Prepared, resident: frozenset[int]) -> list[int] | None:
    values = [FULL, *(prepared.signals[signal] for signal in sorted(resident))]
    coefficients = span_coefficients(values, logo_truth_table())
    if coefficients is None:
        return None
    support = []
    for index, signal in enumerate([0, *sorted(resident)]):
        if coefficients & (1 << index) and signal != 0:
            support.append(signal)
    return support


@dataclass(frozen=True)
class State:
    resident: frozenset[int]
    seen: int
    evaluations: int
    recomputations: int
    trace: tuple[dict, ...]


def _ready(prepared: Prepared, basis: dict[int, tuple[int, int]], node_index: int) -> bool:
    # An affine operand can be formed whenever its exact truth table is in the
    # current resident span.  This is more permissive than requiring every
    # syntactic XAG parent to have a dedicated wire.
    return (
        _reduce_with_basis(basis, prepared.left[node_index]) is not None
        and _reduce_with_basis(basis, prepared.right[node_index]) is not None
    )


def _eviction_candidates(prepared: Prepared, resident: frozenset[int], node: int) -> list[int]:
    # Inputs are not rematerialized: only nonlinear residents may be spilled.
    candidates = [signal for signal in resident if signal >= 13 and signal != node]
    return sorted(candidates)


def _add_node(prepared: Prepared, state: State, node_index: int) -> list[State]:
    node = 13 + node_index
    basis = state_basis(prepared, state.resident)
    if not _ready(prepared, basis, node_index):
        return []
    signal_in_span = _reduce_with_basis(basis, prepared.signals[node]) is not None
    if signal_in_span:
        return []
    evaluations = state.evaluations + 1
    recomputations = state.recomputations + int(bool(state.seen & (1 << node_index)))
    new_resident = set(state.resident)
    new_resident.add(node)
    base_rank = resident_rank(prepared, frozenset(new_resident))
    victims: list[int | None]
    if base_rank <= WIRE_LIMIT:
        victims = [None]
    else:
        victims = _eviction_candidates(prepared, frozenset(new_resident), node)
    result = []
    for victim in victims:
        if victim is None:
            candidate = frozenset(new_resident)
        else:
            candidate = frozenset(signal for signal in new_resident if signal != victim)
        if resident_rank(prepared, candidate) > WIRE_LIMIT:
            continue
        result.append(State(
            resident=candidate,
            seen=state.seen | (1 << node_index),
            evaluations=evaluations,
            recomputations=recomputations,
            trace=state.trace + ({
                "action": "compute" if not (state.seen & (1 << node_index)) else "recompute",
                "node": node,
                "evicted": victim,
                "rank": resident_rank(prepared, candidate),
                "resident": sorted(candidate),
            },),
        ))
    return result


def _score(prepared: Prepared, state: State, frontier: int) -> tuple:
    rank_now = resident_rank(prepared, state.resident)
    # Prefer phase progress/ready frontier, then fewer evaluations and lower
    # rank. The beam remains a feasibility screen, not a depth optimizer.
    return (-frontier, state.recomputations, state.evaluations, rank_now, len(state.resident))


def search(prepared: Prepared, budget: int, beam_width: int = 2000) -> dict:
    initial = State(INPUTS, 0, 0, 0, tuple())
    beam = [initial]
    best = initial
    seen_keys = set()
    for _ in range(len(prepared.parsed.nodes) * 3):
        candidates: list[State] = []
        for state in beam:
            support = phase_support(prepared, state.resident)
            if support is not None:
                best = state
                return _result(prepared, budget, state, True, support, beam_width)
            for node_index in range(len(prepared.parsed.nodes)):
                for child in _add_node(prepared, state, node_index):
                    if child.recomputations > budget:
                        continue
                    key = (child.resident, child.seen, child.evaluations)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    candidates.append(child)
        if not candidates:
            break
        candidates.sort(key=lambda state: _score(prepared, state, state.seen.bit_count()))
        beam = candidates[:beam_width]
        best = beam[0]
    return _result(prepared, budget, best, False, None, beam_width)


def _result(prepared: Prepared, budget: int, state: State, success: bool, support: list[int] | None, beam_width: int) -> dict:
    return {
        "search_type": "bounded_beam_heuristic",
        "exact_semantic_verification": True,
        "impossibility_proof": False,
        "xag": "artifacts/multiplicative_depth/seeds/shared_rank.xag",
        "and_count": len(prepared.parsed.nodes),
        "budget": budget,
        "beam_width": beam_width,
        "success": success,
        "phase_support": support,
        "maximum_rank": max([18, *(event["rank"] for event in state.trace)]),
        "total_and_evaluations": state.evaluations,
        "distinct_and_nodes": state.seen.bit_count(),
        "recomputations": state.recomputations,
        "resident_final": sorted(state.resident),
        "trace": list(state.trace),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--xag", type=Path, default=ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag")
    parser.add_argument("--budgets", type=int, nargs="*", default=[0, 4, 8, 12, 20, 30])
    parser.add_argument("--beam-width", type=int, default=2000)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/destructive_xag_scheduler.json")
    args = parser.parse_args()
    prepared = prepare(args.xag)
    results = [search(prepared, budget, args.beam_width) for budget in args.budgets]
    report = {"budgets": results}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "budgets": [
            {key: row[key] for key in ("budget", "success", "maximum_rank", "total_and_evaluations", "recomputations")}
            for row in results
        ]
    }, indent=2))


if __name__ == "__main__":
    main()
