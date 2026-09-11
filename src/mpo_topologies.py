"""Deterministic two-qubit matching topologies for MPO-native experiments."""

from __future__ import annotations

from typing import Iterable, Sequence

N_QUBITS = 12
TT_ORDER = (0, 1, 2, 3, 4, 5, 11, 8, 6, 7, 9, 10)


def matching_pairs(order: Sequence[int]) -> tuple[tuple[int, int], ...]:
    """Pair consecutive entries; require an even-length permutation."""
    order = tuple(order)
    if len(order) % 2 or len(set(order)) != len(order):
        raise ValueError("matching order must contain distinct even-length entries")
    return tuple((order[i], order[i + 1]) for i in range(0, len(order), 2))


def tt_brickwall_layers(n_qubits: int = N_QUBITS) -> list[tuple[tuple[int, int], ...]]:
    """Return alternating adjacent matchings in the specified TT order."""
    if n_qubits != len(TT_ORDER):
        raise ValueError("the current TT topology is defined for 12 qubits")
    return [
        matching_pairs(TT_ORDER),
        matching_pairs(TT_ORDER[1:-1]),
    ]


def round_robin_matchings(n_qubits: int = N_QUBITS) -> list[tuple[tuple[int, int], ...]]:
    """Generate the 1-factorization of K_n for even n.

    The circle method produces n-1 perfect matchings covering each unordered
    qubit pair exactly once.  The fixed point at the end is not a physical
    qubit and is rotated deterministically.
    """
    if n_qubits % 2:
        raise ValueError("round-robin factorization requires an even number")
    fixed = n_qubits - 1
    rotating = list(range(n_qubits - 1))
    result = []
    for _ in range(n_qubits - 1):
        pairs = [(fixed, rotating[-1])]
        # The final rotating entry is already paired with the fixed point.
        pairs.extend((rotating[i], rotating[-i - 2]) for i in range((n_qubits - 2) // 2))
        result.append(tuple(sorted(tuple(sorted(pair)) for pair in pairs)))
        rotating = [rotating[-1], *rotating[:-1]]
    return result


def xy_matchings() -> list[tuple[tuple[int, int], ...]]:
    """Return simple cross-register perfect matchings for x bits and y bits."""
    x = range(6)
    y = range(6, 12)
    return [
        tuple(zip(x, y)),
        tuple(zip(x, reversed(tuple(y)))),
    ]


def validate_matchings(matchings: Iterable[Sequence[tuple[int, int]]]) -> None:
    """Assert every layer is disjoint and every pair is a valid qubit pair."""
    for layer in matchings:
        used = set()
        for a, b in layer:
            if not (0 <= a < N_QUBITS and 0 <= b < N_QUBITS and a != b):
                raise ValueError(f"invalid pair {(a, b)}")
            if a in used or b in used:
                raise ValueError(f"non-disjoint layer {layer}")
            used.update((a, b))


if __name__ == "__main__":
    rr = round_robin_matchings()
    validate_matchings(rr)
    pairs = {tuple(sorted(pair)) for layer in rr for pair in layer}
    assert len(rr) == 11 and len(pairs) == 66
    validate_matchings(tt_brickwall_layers())
    validate_matchings(xy_matchings())
    print({"round_robin_layers": len(rr), "covered_pairs": len(pairs), "tt": tt_brickwall_layers(), "xy": xy_matchings()})
