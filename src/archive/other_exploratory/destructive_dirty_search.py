"""Semantic search over the actual 18-wire dirty-target state.

Unlike the named-signal scheduler, this model stores the physical affine span
itself. A guided XAG product p=a&b may be injected into any current affine
basis direction h, producing h XOR p. The target is allowed to be any wire,
including an original coordinate wire. This is a space-only experiment; it
does not synthesize the affine CNOT frame or native RCCX gates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from md_xag import FULL, XAG, input_truth_tables, logo_truth_table, mask_indices
from destructive_xag import load_xag
from destructive_xag_scheduler import _basis, _reduce_with_basis


ROOT = Path(__file__).resolve().parents[1]
WIRE_COUNT = 18


def canonical_span(vectors: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    """Canonical nonconstant basis for span({FULL} union vectors)."""

    basis = _basis(sorted(set([FULL, *vectors]), reverse=True))
    result = [value for value, _ in basis.values() if value != FULL]
    return tuple(sorted(result))


def span_basis(state: "DirtyState") -> dict[int, tuple[int, int]]:
    return _basis([FULL, *state.basis])


def contains(state: "DirtyState", value: int) -> bool:
    return _reduce_with_basis(span_basis(state), value) is not None


@dataclass(frozen=True)
class DirtyState:
    basis: tuple[int, ...]
    used_products: int
    evaluations: int
    trace: tuple[dict, ...]


@dataclass(frozen=True)
class RepeatedDirtyState:
    basis: tuple[int, ...]
    evaluations: int
    trace: tuple[dict, ...]


def prepare_products(path: Path) -> tuple[DirtyState, tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    parsed = load_xag(path)
    graph: XAG = parsed.graph
    signals = tuple(graph._signals())
    left = []
    right = []
    products = []
    for node in parsed.nodes:
        forms = []
        for mask in (node.left_affine_mask, node.right_affine_mask):
            value = 0
            for signal in mask_indices(mask):
                value ^= FULL if signal == 0 else signals[signal]
            forms.append(value)
        left.append(forms[0])
        right.append(forms[1])
        products.append(forms[0] & forms[1])
    initial = canonical_span(input_truth_tables() + [0] * 6)
    return DirtyState(initial, 0, 0, tuple()), tuple(left), tuple(right), tuple(products)


def phase_support(state: DirtyState) -> list[int] | None:
    coefficients = _reduce_with_basis(span_basis(state), logo_truth_table())
    if coefficients is None:
        return None
    # The exact physical-wire support is intentionally left symbolic here;
    # this coefficient mask is over the canonical affine basis, not fixed q's.
    return [index for index in range(len(state.basis)) if coefficients & (1 << (index + 1))]


def search(path: Path, beam_width: int = 500, max_evaluations: int = 97) -> dict:
    initial, left, right, products = prepare_products(path)
    beam = [initial]
    best = initial
    for step in range(max_evaluations):
        candidates: list[DirtyState] = []
        for state in beam:
            if phase_support(state) is not None:
                return result(state, True, beam_width, max_evaluations)
            basis = span_basis(state)
            for index, product in enumerate(products):
                if state.used_products & (1 << index):
                    continue
                if _reduce_with_basis(basis, left[index]) is None:
                    continue
                if _reduce_with_basis(basis, right[index]) is None:
                    continue
                if _reduce_with_basis(basis, product) is not None:
                    continue
                targets = [(None, canonical_span(list(state.basis) + [product]))]
                if len(state.basis) >= WIRE_COUNT:
                    targets = [
                        (target, canonical_span(
                            [value for value in state.basis if value != target]
                            + [target ^ product]
                        ))
                        for target in state.basis
                    ]
                for target, new_basis in targets:
                    if len(new_basis) > WIRE_COUNT:
                        continue
                    candidates.append(DirtyState(
                        basis=new_basis,
                        used_products=state.used_products | (1 << index),
                        evaluations=state.evaluations + 1,
                        trace=state.trace + ({
                            "product": index + 13,
                            "target_basis": target,
                            "rank_including_constant": len(new_basis) + 1,
                            "basis_size": len(new_basis),
                        },),
                    ))
        if not candidates:
            break
        # Prefer states that expose many additional XAG products. Compute the
        # span basis once per candidate; repeated full truth-table elimination
        # here otherwise dominates the search.
        scored = []
        for state in candidates:
            b = span_basis(state)
            ready = sum(
                _reduce_with_basis(b, left[i]) is not None
                and _reduce_with_basis(b, right[i]) is not None
                for i in range(len(products))
                if not (state.used_products & (1 << i))
            )
            scored.append(((-ready, state.evaluations, state.basis), state))
        scored.sort(key=lambda item: item[0])
        candidates = [state for _, state in scored]
        beam = candidates[:beam_width]
        best = beam[0]
    return result(best, False, beam_width, max_evaluations)


def output_cone(path: Path) -> set[int]:
    parsed = load_xag(path)
    cone = {signal for signal in mask_indices(parsed.output_affine_mask) if signal >= 13}
    stack = list(cone)
    while stack:
        node = stack.pop()
        index = node - 13
        for mask in (parsed.nodes[index].left_affine_mask, parsed.nodes[index].right_affine_mask):
            for signal in mask_indices(mask):
                if signal >= 13 and signal not in cone:
                    cone.add(signal)
                    stack.append(signal)
    return cone


def _repeated_features(state: RepeatedDirtyState, left, right, products, cone, signals):
    basis = span_basis(DirtyState(state.basis, 0, state.evaluations, state.trace))
    cone_available = sum(
        _reduce_with_basis(basis, signals[node]) is not None for node in cone
    )
    cone_ready = 0
    total_ready = 0
    for index, product in enumerate(products):
        operands_ready = (
            _reduce_with_basis(basis, left[index]) is not None
            and _reduce_with_basis(basis, right[index]) is not None
        )
        if operands_ready and _reduce_with_basis(basis, product) is None:
            total_ready += 1
            if index + 13 in cone:
                cone_ready += 1
    return cone_available, cone_ready, total_ready


def repeated_search(path: Path, beam_width: int = 50, max_evaluations: int = 120) -> dict:
    """Search the physical affine span while permitting product repeats.

    States are deduplicated by their canonical affine span at each evaluation
    depth. Product history is deliberately absent from the state key.
    """

    initial, left, right, products = prepare_products(path)
    parsed = load_xag(path)
    signals = tuple(parsed.graph._signals())
    cone = output_cone(path)
    feature_cache = {}
    phase_cache = {}

    def features_for_basis(basis_tuple):
        if basis_tuple in feature_cache:
            return feature_cache[basis_tuple]
        probe = RepeatedDirtyState(basis_tuple, 0, tuple())
        value = _repeated_features(probe, left, right, products, cone, signals)
        feature_cache[basis_tuple] = value
        return value

    def phase_for_basis(basis_tuple):
        if basis_tuple not in phase_cache:
            phase_cache[basis_tuple] = phase_support(
                DirtyState(basis_tuple, 0, 0, tuple())
            )
        return phase_cache[basis_tuple]

    beam = [RepeatedDirtyState(initial.basis, 0, tuple())]
    termination = "evaluation_budget"
    for step in range(max_evaluations + 1):
        for state in beam:
            support = phase_for_basis(state.basis)
            if support is not None:
                return repeated_result(
                    state, True, termination, beam_width, max_evaluations, cone, signals,
                )
        if step == max_evaluations:
            break
        candidates: dict[tuple[int, ...], RepeatedDirtyState] = {}
        for state in beam:
            basis = span_basis(DirtyState(state.basis, 0, state.evaluations, state.trace))
            ready = []
            for index, product in enumerate(products):
                if _reduce_with_basis(basis, left[index]) is None:
                    continue
                if _reduce_with_basis(basis, right[index]) is None:
                    continue
                if _reduce_with_basis(basis, product) is not None:
                    continue
                ready.append((index, product))
            for index, product in ready:
                if len(state.basis) < WIRE_COUNT:
                    targets = [(None, canonical_span(list(state.basis) + [product]))]
                else:
                    targets = [
                        (target, canonical_span(
                            [value for value in state.basis if value != target]
                            + [target ^ product]
                        ))
                        for target in state.basis
                    ]
                for target, new_basis in targets:
                    if len(new_basis) > WIRE_COUNT:
                        continue
                    trace = state.trace + ({
                        "evaluation": state.evaluations + 1,
                        "product": index + 13,
                        "target_basis": target,
                        "rank_including_constant": len(new_basis) + 1,
                    },)
                    child = RepeatedDirtyState(new_basis, state.evaluations + 1, trace)
                    prior = candidates.get(new_basis)
                    if prior is None or len(child.trace) < len(prior.trace):
                        candidates[new_basis] = child
        if not candidates:
            termination = "no_guided_transition"
            break
        scored = []
        for state in candidates.values():
            features = features_for_basis(state.basis)
            # Output-cone availability dominates general readiness. All states
            # at one layer have equal evaluation count, but retaining it in the
            # key makes the policy explicit and deterministic.
            scored.append(((-features[0], -features[1], -features[2], state.evaluations, state.basis), state))
        scored.sort(key=lambda item: item[0])
        beam = [state for _, state in scored[:beam_width]]
    best = beam[0]
    return repeated_result(best, False, termination, beam_width, max_evaluations, cone, signals)


def repeated_result(state: RepeatedDirtyState, success: bool, termination: str,
                    beam_width: int, max_evaluations: int, cone: set[int], signals) -> dict:
    product_ids = [event["product"] for event in state.trace]
    support = phase_support(DirtyState(state.basis, 0, state.evaluations, state.trace))
    return {
        "search_type": "physical_dirty_affine_span_repeated_products",
        "exact_semantic_verification": True,
        "impossibility_proof": False,
        "success": success,
        "termination": termination,
        "beam_width": beam_width,
        "max_evaluations": max_evaluations,
        "total_product_evaluations": state.evaluations,
        "unique_product_count": len(set(product_ids)),
        "repeated_product_evaluations": len(product_ids) - len(set(product_ids)),
        "maximum_affine_rank_including_constant": len(state.basis) + 1,
        "output_cone_size": len(cone),
        "output_cone_available": _repeated_features(state, (), (), (), cone, signals)[0],
        "phase_support_in_canonical_basis": support,
        "final_basis_size": len(state.basis),
        "trace": list(state.trace),
    }


def result(state: DirtyState, success: bool, beam_width: int, max_evaluations: int) -> dict:
    return {
        "search_type": "physical_dirty_affine_span",
        "exact_semantic_verification": True,
        "impossibility_proof": False,
        "success": success,
        "beam_width": beam_width,
        "max_evaluations": max_evaluations,
        "total_product_evaluations": state.evaluations,
        "maximum_affine_rank_including_constant": max([13, len(state.basis) + 1]),
        "phase_support_in_canonical_basis": phase_support(state),
        "final_basis_size": len(state.basis),
        "trace": list(state.trace),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--xag", type=Path, default=ROOT / "artifacts/multiplicative_depth/seeds/shared_rank.xag")
    parser.add_argument("--beam-width", type=int, default=500)
    parser.add_argument("--max-evaluations", type=int, default=97)
    parser.add_argument("--allow-repeats", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/destructive_dirty_search.json")
    args = parser.parse_args()
    report = (
        repeated_search(args.xag, args.beam_width, args.max_evaluations)
        if args.allow_repeats
        else search(args.xag, args.beam_width, args.max_evaluations)
    )
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "trace"}, indent=2))


if __name__ == "__main__":
    main()
