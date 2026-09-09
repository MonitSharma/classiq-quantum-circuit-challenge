"""Heuristic dirty-output frame search for the joint y-feature graph.

This is an abstract reversible-frame search, not yet a gate compiler.  A wire
is represented by its 64-row Boolean truth mask.  A shared product node may be
toggled into a dirty wire when both of its affine control forms lie in the
linear span of the other wires and the six y inputs.  The goal is to find six
wire functions whose span contains all five desired outputs while having only
five non-affine dimensions, allowing one wire to be cleared by a final linear
frame transform.
"""

from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path

from vector_reversible_pebble import FULL, INPUT_TT, form_value, parse

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
SOURCE = ARTIFACTS / "vector_feature_abc_strash_balance_rewrite_refactor_resub.bench"


def reduce_basis(values: list[int]) -> list[int]:
    basis: dict[int, int] = {}
    for value in values:
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                break
    return [basis[pivot] for pivot in sorted(basis, reverse=True)]


def rank(values: list[int]) -> int:
    return len(reduce_basis(values))


def in_span(value: int, values: list[int]) -> bool:
    return rank(values + [value]) == rank(values)


def in_basis(value: int, basis: tuple[int, ...] | list[int]) -> bool:
    for pivot in basis:
        if value and (value >> (pivot.bit_length() - 1)) & 1:
            value ^= pivot
    return value == 0


def quotient_rank(values: list[int], base: list[int]) -> int:
    return rank(base + values) - rank(base)


@lru_cache(maxsize=200_000)
def cached_basis(values: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(reduce_basis(list(values)))


def state_score(wires: tuple[int, ...], base: list[int], targets: list[int]) -> tuple:
    span = cached_basis(tuple(base) + wires)
    covered = sum(in_basis(target, span) for target in targets)
    qrank = len(span) - len(cached_basis(tuple(base)))
    target_rank = len(cached_basis(tuple(base) + tuple(targets))) - len(cached_basis(tuple(base)))
    return (covered, -abs(target_rank - qrank), qrank)


def main() -> None:
    graph = parse(SOURCE)
    base = [FULL, *INPUT_TT]
    targets = [form_value(form, graph.truth) for form in graph.outputs.values()]
    nodes = sorted(graph.nodes)
    node_truth = {node: graph.truth[node] for node in nodes}
    node_controls = {
        node: (form_value(left, graph.truth), form_value(right, graph.truth))
        for node, (left, right) in graph.nodes.items()
    }
    rng = random.Random(531)
    beam: dict[tuple[int, ...], dict] = {(0, 0, 0, 0, 0, 0): {"path": []}}
    best = None
    best_score = (-1, -999, -1)
    records = []
    target_rank = len(reduce_basis(base + targets)) - len(reduce_basis(base))
    base_basis = reduce_basis(base)
    for depth in range(1, 13):
        candidates: dict[tuple[int, ...], dict] = {}
        for wires, metadata in beam.items():
            for node in nodes:
                left, right = node_controls[node]
                for target in range(6):
                    # Abstract frame screen: permit the current target frame
                    # in the control span.  This is intentionally optimistic;
                    # the physical compiler must later replace any such step
                    # with a dirty-control construction that keeps target and
                    # controls disjoint.
                    available = cached_basis(tuple(base + list(wires)))
                    if not in_basis(left, available) or not in_basis(right, available):
                        continue
                    updated = list(wires)
                    updated[target] ^= node_truth[node]
                    updated = tuple(sorted(updated))
                    if updated == wires:
                        continue
                    path = metadata["path"] + [(node, target)]
                    previous = candidates.get(updated)
                    if previous is None or len(path) < len(previous["path"]):
                        candidates[updated] = {"path": path}
        scored = sorted(
            candidates.items(),
            key=lambda item: state_score(item[0], base, targets),
            reverse=True,
        )
        # Keep a diverse beam: prioritize score but retain random ties.
        keep = scored[:1000]
        if len(scored) > 1000:
            tail = scored[1000:]
            keep.extend(rng.sample(tail, min(64, len(tail))))
        beam = dict(keep)
        if not beam:
            break
        current = max(
            ((state_score(wires, base, targets), wires, meta) for wires, meta in beam.items()),
            key=lambda item: item[0],
        )
        score_value, wires, metadata = current
        records.append({"depth": depth, "states": len(candidates), "beam": len(beam),
                        "best_score": score_value, "wires": list(wires)})
        if score_value > best_score:
            best_score, best_wires, best_metadata = score_value, wires, metadata
            best = True
        if score_value[0] == 5 and score_value[2] == target_rank:
            break
    result = {
        "source": str(SOURCE.relative_to(SOURCE.parents[1])),
        "target_count": len(targets),
        "target_quotient_rank": quotient_rank(targets, base),
        "best_score": best_score,
        "best_wires": list(best_wires) if best else None,
        "best_path": best_metadata["path"] if best else None,
        "records": records,
        "note": "Abstract frame search only; each node toggle still requires physical dirty-control synthesis and phase verification.",
    }
    (ARTIFACTS / "vector_dirty_frame_search.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps({
        "target_quotient_rank": result["target_quotient_rank"],
        "best_score": result["best_score"],
        "best_path_length": len(result["best_path"] or []),
    }, indent=2))


if __name__ == "__main__":
    main()
