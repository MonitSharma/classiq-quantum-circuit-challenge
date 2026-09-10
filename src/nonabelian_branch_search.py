"""Finite-group search prototype for a width-2 phase branching program.

An instruction chooses one of two elements of the binary icosahedral group
according to one coordinate bit.  The product must finish at +1 or -1,
depending on the logo predicate.  The search is intentionally classical:
all 4096 input trajectories are evaluated by table lookup before any quantum
decomposition is attempted.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from pathlib import Path

from search import logo


GROUP_ORDER = 120
IDENTITY = 1
PHI = (1.0 + math.sqrt(5.0)) / 2.0


def _key(values: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(round(value, 12) for value in values)


def _binary_icosahedral_elements() -> list[tuple[float, ...]]:
    """Return the 120 unit quaternions of the binary icosahedral group."""
    elements: list[tuple[float, ...]] = []

    def add(values: list[float]) -> None:
        value = _key(tuple(values))
        if value not in elements:
            elements.append(value)

    for position in range(4):
        for sign in (-1.0, 1.0):
            values = [0.0] * 4
            values[position] = sign
            add(values)
    for signs in itertools.product((-1.0, 1.0), repeat=4):
        add([sign * 0.5 for sign in signs])

    base = (0.0, 0.5, 0.5 * PHI, 0.5 / PHI)
    for permutation in itertools.permutations(range(4)):
        inversions = sum(
            permutation[i] > permutation[j]
            for i in range(4)
            for j in range(i + 1, 4)
        )
        if inversions % 2:
            continue
        for signs in itertools.product((-1.0, 1.0), repeat=4):
            add([signs[i] * base[permutation[i]] for i in range(4)])
    if len(elements) != GROUP_ORDER:
        raise AssertionError(len(elements))
    return elements


def _quaternion_product(
    left: tuple[float, ...], right: tuple[float, ...]
) -> tuple[float, ...]:
    w, x, y, z = left
    W, X, Y, Z = right
    return (
        w * W - x * X - y * Y - z * Z,
        w * X + x * W + y * Z - z * Y,
        w * Y - x * Z + y * W + z * X,
        w * Z + x * Y - y * X + z * W,
    )


ELEMENTS = _binary_icosahedral_elements()
ELEMENT_INDEX = {element: index for index, element in enumerate(ELEMENTS)}
MULTIPLY = [
    [
        ELEMENT_INDEX[_key(_quaternion_product(left, right))]
        for right in ELEMENTS
    ]
    for left in ELEMENTS
]
MINUS_IDENTITY = ELEMENT_INDEX[(-1.0, 0.0, 0.0, 0.0)]
CENTRAL = {IDENTITY, MINUS_IDENTITY}


def target_signs() -> tuple[int, ...]:
    return tuple(
        MINUS_IDENTITY if logo(x, y) else IDENTITY
        for y in range(64)
        for x in range(64)
    )


TARGET = target_signs()
BIT_VALUES = tuple(
    tuple((index >> bit) & 1 for index in range(4096))
    for bit in range(12)
)


Instruction = tuple[int, int, int]


def evaluate(program: tuple[Instruction, ...]) -> tuple[int, ...]:
    states = [IDENTITY] * 4096
    for bit, zero, one in program:
        row = MULTIPLY[zero]
        alternate = MULTIPLY[one]
        values = BIT_VALUES[bit]
        states = [
            (alternate[state] if values[index] else row[state])
            for index, state in enumerate(states)
        ]
    return tuple(states)


def score(states: tuple[int, ...]) -> int:
    return sum(actual != expected for actual, expected in zip(states, TARGET))


def random_instruction(rng: random.Random) -> Instruction:
    return rng.randrange(12), rng.randrange(GROUP_ORDER), rng.randrange(GROUP_ORDER)


def search(length: int, iterations: int, seed: int) -> tuple[tuple[Instruction, ...], int]:
    rng = random.Random(seed)
    best_program: tuple[Instruction, ...] | None = None
    best_score = 4096
    for restart in range(max(1, iterations // 2000)):
        program = tuple(random_instruction(rng) for _ in range(length))
        current_score = score(evaluate(program))
        temperature = max(2.0, current_score / 32.0)
        for _ in range(2000):
            position = rng.randrange(length)
            candidate = list(program)
            candidate[position] = random_instruction(rng)
            candidate_program = tuple(candidate)
            candidate_score = score(evaluate(candidate_program))
            delta = candidate_score - current_score
            if delta <= 0 or rng.random() < math.exp(-delta / temperature):
                program, current_score = candidate_program, candidate_score
            temperature = max(0.05, temperature * 0.997)
            if current_score < best_score:
                best_program, best_score = program, current_score
                print(json.dumps({
                    "restart": restart,
                    "score": best_score,
                    "length": length,
                }), flush=True)
                if best_score == 0:
                    return best_program, best_score
    if best_program is None:
        raise AssertionError("search produced no candidate")
    return best_program, best_score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--length", type=int, default=16)
    parser.add_argument("--iterations", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if len(ELEMENTS) != GROUP_ORDER or len(MULTIPLY) != GROUP_ORDER:
        raise AssertionError("invalid group table")
    program, mismatches = search(args.length, args.iterations, args.seed)
    payload = {
        "group": "binary_icosahedral",
        "group_order": GROUP_ORDER,
        "length": args.length,
        "iterations": args.iterations,
        "seed": args.seed,
        "target_marked_states": sum(value == MINUS_IDENTITY for value in TARGET),
        "mismatches": mismatches,
        "program": [list(item) for item in program],
        "status": "exact" if mismatches == 0 else "incomplete",
    }
    print(json.dumps(payload, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
