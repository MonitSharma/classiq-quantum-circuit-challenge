"""Small exact MPO contractions for the first MPO-native smoke experiments."""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

from mpo_target import DEFAULT_ORDER, DIM, diagonal_mpo, tt_svd, ordered_tensor


def mpo_core_from_target(core: np.ndarray) -> np.ndarray:
    """Convert target core (left,right,input,output) to (left,input,output,right)."""
    return np.transpose(core, (0, 2, 3, 1))


def target_mpo(order: Sequence[int] = DEFAULT_ORDER) -> list[np.ndarray]:
    cores, _ = tt_svd(ordered_tensor(order))
    return [mpo_core_from_target(core) for core in diagonal_mpo(cores)]


def identity_mpo(n_sites: int = 12) -> list[np.ndarray]:
    eye = np.eye(2, dtype=np.complex128).reshape(1, 2, 2, 1)
    return [eye.copy() for _ in range(n_sites)]


def apply_adjacent_gate(
    mpo: Sequence[np.ndarray], slot: int, gate: np.ndarray, max_bond: int | None = None
) -> list[np.ndarray]:
    """Left-apply a two-site gate and split it back into an MPO.

    The gate matrix uses the same two-site basis convention as Qiskit's
    ``UnitaryGate``.  With no ``max_bond`` this is an exact SVD split.
    """
    if not 0 <= slot < len(mpo) - 1:
        raise ValueError("slot must identify adjacent MPO sites")
    gate = np.asarray(gate, dtype=np.complex128).reshape(2, 2, 2, 2)
    left, right = mpo[slot], mpo[slot + 1]
    # Contract the gate with the *output* legs (u,v) of the current MPO;
    # preserve the old input legs (a,b) for the resulting operator.
    merged = np.einsum("cduv,iaum,mbvr->iabcdr", gate, left, right)
    # Group (left bond, first input, first output) versus
    # (second input, second output, right bond).
    merged = np.transpose(merged, (0, 1, 3, 2, 4, 5))
    shape = merged.shape
    matrix = merged.reshape(shape[0] * shape[1] * shape[2], -1)
    u, singular, vh = np.linalg.svd(matrix, full_matrices=False)
    rank = len(singular) if max_bond is None else min(len(singular), max_bond)
    u = u[:, :rank]
    svh = singular[:rank, None] * vh[:rank]
    new_left = u.reshape(shape[0], shape[1], shape[3], rank)
    new_right = svh.reshape(rank, shape[2], shape[4], shape[5])
    out = list(mpo)
    out[slot : slot + 2] = [new_left, new_right]
    return out


def apply_layer(
    mpo: Sequence[np.ndarray], gates: Mapping[int, np.ndarray], max_bond: int | None = None
) -> list[np.ndarray]:
    """Apply disjoint adjacent gates, from left to right."""
    out = list(mpo)
    for slot in sorted(gates):
        out = apply_adjacent_gate(out, slot, gates[slot], max_bond=max_bond)
    return out


def hilbert_schmidt_overlap(left: Sequence[np.ndarray], right: Sequence[np.ndarray]) -> complex:
    """Return ``Tr(left† right)`` by contracting two MPOs."""
    if len(left) != len(right):
        raise ValueError("MPO lengths differ")
    env = np.ones((1, 1), dtype=np.complex128)
    for a, b in zip(left, right):
        env = np.einsum("ab,aioc,biod->cd", env, a.conj(), b)
    return complex(np.squeeze(env))


def process_fidelity(candidate: Sequence[np.ndarray], target: Sequence[np.ndarray]) -> float:
    overlap = hilbert_schmidt_overlap(target, candidate)
    dimension = 2 ** len(candidate)
    return float(abs(overlap) ** 2 / dimension**2)
