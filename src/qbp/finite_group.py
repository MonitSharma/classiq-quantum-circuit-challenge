"""Exact finite-group width-2 QBP model.

The group table is represented by integer indices, so terminal constraints are
exact.  Quaternion coordinates are retained only to build the binary
icosahedral multiplication table and to support later controlled-unitary
calibration.
"""

from __future__ import annotations

import itertools
import math
from typing import Iterable

from search import logo


PHI = (1.0 + math.sqrt(5.0)) / 2.0
GROUP_ORDER = 120
IDENTITY = 1


def _key(values: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(round(value, 12) for value in values)


def elements() -> list[tuple[float, ...]]:
    result: list[tuple[float, ...]] = []

    def add(values: list[float]) -> None:
        value = _key(tuple(values))
        if value not in result:
            result.append(value)

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
            for i in range(4) for j in range(i + 1, 4)
        )
        if inversions % 2:
            continue
        for signs in itertools.product((-1.0, 1.0), repeat=4):
            add([signs[i] * base[permutation[i]] for i in range(4)])
    if len(result) != GROUP_ORDER:
        raise AssertionError(len(result))
    return result


ELEMENTS = elements()
ELEMENT_INDEX = {element: index for index, element in enumerate(ELEMENTS)}


def quaternion_product(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    w, x, y, z = left
    W, X, Y, Z = right
    return (
        w * W - x * X - y * Y - z * Z,
        w * X + x * W + y * Z - z * Y,
        w * Y - x * Z + y * W + z * X,
        w * Z + x * Y - y * X + z * W,
    )


MULTIPLY = [
    [ELEMENT_INDEX[_key(quaternion_product(left, right))] for right in ELEMENTS]
    for left in ELEMENTS
]
MINUS_IDENTITY = ELEMENT_INDEX[(-1.0, 0.0, 0.0, 0.0)]
CENTRAL = {IDENTITY, MINUS_IDENTITY}


def _inverse(element: int) -> int:
    for candidate in range(GROUP_ORDER):
        if MULTIPLY[element][candidate] == IDENTITY and MULTIPLY[candidate][element] == IDENTITY:
            return candidate
    raise AssertionError(element)


INVERSE = tuple(_inverse(element) for element in range(GROUP_ORDER))


def conjugate(conjugator: int, element: int) -> int:
    """Return conjugator^-1 * element * conjugator."""
    return MULTIPLY[MULTIPLY[INVERSE[conjugator]][element]][conjugator]


def conjugacy_class(element: int) -> frozenset[int]:
    return frozenset(conjugate(h, element) for h in range(GROUP_ORDER))


CONJUGACY_REPRESENTATIVES = tuple(sorted({min(conjugacy_class(element)) for element in range(GROUP_ORDER)}))


def centralizer_orbit_representatives(element: int) -> tuple[int, ...]:
    centralizer = [h for h in range(GROUP_ORDER) if conjugate(h, element) == element]
    unseen = set(range(GROUP_ORDER))
    reps = []
    while unseen:
        value = min(unseen)
        orbit = {conjugate(h, value) for h in centralizer}
        reps.append(value)
        unseen -= orbit
    return tuple(sorted(reps))


CENTRALIZER_ORBIT_REPS = {
    rep: centralizer_orbit_representatives(rep)
    for rep in CONJUGACY_REPRESENTATIVES
}

TARGET = tuple(
    MINUS_IDENTITY if logo(x, y) else IDENTITY
    for y in range(64) for x in range(64)
)
BIT_VALUES = tuple(
    tuple((index >> bit) & 1 for index in range(4096))
    for bit in range(12)
)

Instruction = tuple[int, int, int]


def evaluate(program: Iterable[Instruction]) -> tuple[int, ...]:
    states = [IDENTITY] * 4096
    for bit, zero, one in program:
        zero_row = MULTIPLY[zero]
        one_row = MULTIPLY[one]
        values = BIT_VALUES[bit]
        states = [
            (one_row[state] if values[index] else zero_row[state])
            for index, state in enumerate(states)
        ]
    return tuple(states)


def mismatch_count(program: Iterable[Instruction]) -> int:
    return sum(actual != expected for actual, expected in zip(evaluate(program), TARGET))
