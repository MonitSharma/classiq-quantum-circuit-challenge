"""Exhaustive self-test for the destructive semantic engine.

This is intentionally independent of Qiskit: a random reversible gate history
is replayed once with Python bits and once with the 4096-bit truth-table
helpers, then every physical wire is compared on every coordinate input.
"""

from __future__ import annotations

import random

from destructive_semantic_search import (
    ALL_ONES,
    TARGET,
    apply_cx_semantic,
    apply_rccx_semantic,
    apply_x_semantic,
    affine_span_solution,
    initial_wire_truth_tables,
)


def _mask(values: list[int]) -> int:
    result = 0
    for index, value in enumerate(values):
        result |= (value & 1) << index
    return result


def main() -> None:
    assert TARGET.bit_count() == 1097
    initial = initial_wire_truth_tables()
    assert len(initial) == 18
    assert initial[12:] == (0,) * 6
    assert all((value & ~ALL_ONES) == 0 for value in initial)

    # Check the primitives on every one of the 4096 coordinate assignments.
    rng = random.Random(20261009)
    semantic = initial
    classical = [[(assignment >> wire) & 1 for wire in range(18)]
                 for assignment in range(4096)]
    operations = []
    for _ in range(96):
        kind = rng.choice(("x", "cx", "rccx"))
        if kind == "x":
            target = rng.randrange(18)
            semantic = apply_x_semantic(semantic, target)
            operations.append((kind, target))
            for row in classical:
                row[target] ^= 1
        elif kind == "cx":
            control, target = rng.sample(range(18), 2)
            semantic = apply_cx_semantic(semantic, control, target)
            operations.append((kind, control, target))
            for row in classical:
                row[target] ^= row[control]
        else:
            control, other, target = rng.sample(range(18), 3)
            semantic = apply_rccx_semantic(semantic, control, other, target)
            operations.append((kind, control, other, target))
            for row in classical:
                row[target] ^= row[control] & row[other]

    for wire in range(18):
        assert semantic[wire] == _mask([row[wire] for row in classical]), wire

    # Toy affine-span checks exercise both the constant and multi-wire cases.
    toy = list(initial)
    toy_target = toy[0] ^ toy[1] ^ ALL_ONES
    solution = affine_span_solution(tuple(toy), toy_target)
    assert solution is not None
    assert solution["constant"] == 1
    assert solution["wires"] == [0, 1]

    print({
        "status": "passed",
        "states_checked": 4096,
        "primitive_operations": len(operations),
        "marked_states": TARGET.bit_count(),
        "toy_affine_span": "passed",
    })


if __name__ == "__main__":
    main()
