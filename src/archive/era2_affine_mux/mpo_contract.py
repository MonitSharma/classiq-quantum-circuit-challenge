"""Small exact MPO contractions for the first MPO-native smoke experiments."""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
from qiskit import qasm2

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


def _embedded_local_gate(gate: np.ndarray, n_sites: int, first: int, second: int) -> np.ndarray:
    """Embed a two-site gate in an n-site local basis (first site is MSB)."""
    gate = np.asarray(gate, dtype=np.complex128).reshape(4, 4)
    dimension = 2**n_sites
    embedded = np.zeros((dimension, dimension), dtype=np.complex128)
    for column in range(dimension):
        bits = [(column >> (n_sites - 1 - i)) & 1 for i in range(n_sites)]
        local_column = 2 * bits[first] + bits[second]
        for local_row in range(4):
            row_bits = bits.copy()
            row_bits[first] = local_row >> 1
            row_bits[second] = local_row & 1
            row = sum(bit << (n_sites - 1 - i) for i, bit in enumerate(row_bits))
            embedded[row, column] = gate[local_row, local_column]
    return embedded


def _split_operator_window(tensor: np.ndarray, n_sites: int, max_bond: int | None) -> list[np.ndarray]:
    """Split a window shaped (left, input..., output..., right) into MPO cores."""
    left, _, _, right = tensor.shape
    tensor = tensor.reshape(left, 2**n_sites, 2**n_sites, right)
    tensor = tensor.reshape((left,) + (2,) * n_sites + (2,) * n_sites + (right,))
    permutation = [0]
    for i in range(n_sites):
        permutation.extend((1 + i, 1 + n_sites + i))
    permutation.append(2 * n_sites + 1)
    tensor = np.transpose(tensor, permutation)
    cores = []
    bond = left
    remaining = tensor
    for site in range(n_sites - 1):
        matrix = remaining.reshape(bond * 4, -1)
        u, singular, vh = np.linalg.svd(matrix, full_matrices=False)
        rank = len(singular) if max_bond is None else min(len(singular), max_bond)
        u = u[:, :rank]
        cores.append(u.reshape(bond, 2, 2, rank))
        remaining = (singular[:rank, None] * vh[:rank]).reshape(
            (rank,) + remaining.shape[3:]
        )
        bond = rank
    cores.append(remaining.reshape(bond, 2, 2, right))
    return cores


def apply_nonadjacent_gate(
    mpo: Sequence[np.ndarray], first: int, second: int, gate: np.ndarray, max_bond: int | None = None
) -> list[np.ndarray]:
    """Left-apply a gate to arbitrary sites without physical SWAP gates."""
    if first == second or not (0 <= first < len(mpo) and 0 <= second < len(mpo)):
        raise ValueError("gate sites must be distinct MPO slots")
    if first > second:
        first, second = second, first
    window = list(mpo[first : second + 1])
    merged = window[0]
    for core in window[1:]:
        merged = np.tensordot(merged, core, axes=(-1, 0))
    n_sites = second - first + 1
    # Current merged axes are left, (input,output)*n, right.  Separate them
    # into input and output blocks before applying the embedded gate.
    permutation = [0]
    permutation.extend(1 + 2 * i for i in range(n_sites))
    permutation.extend(2 + 2 * i for i in range(n_sites))
    permutation.append(2 * n_sites + 1)
    merged = np.transpose(merged, permutation)
    left, right = merged.shape[0], merged.shape[-1]
    merged = merged.reshape(left, 2**n_sites, 2**n_sites, right)
    embedded = _embedded_local_gate(gate, n_sites, 0, n_sites - 1)
    merged = np.einsum("co,lior->licr", embedded, merged)
    replacement = _split_operator_window(merged, n_sites, max_bond)
    out = list(mpo)
    out[first : second + 1] = replacement
    return out


def apply_layer(
    mpo: Sequence[np.ndarray], gates: Mapping[int, np.ndarray], max_bond: int | None = None
) -> list[np.ndarray]:
    """Apply disjoint adjacent gates, from left to right."""
    out = list(mpo)
    for slot in sorted(gates):
        out = apply_adjacent_gate(out, slot, gates[slot], max_bond=max_bond)
    return out


def apply_single_qubit(mpo: Sequence[np.ndarray], slot: int, gate: np.ndarray) -> list[np.ndarray]:
    """Left-apply a one-qubit gate to one MPO output leg."""
    if not 0 <= slot < len(mpo):
        raise ValueError("invalid MPO slot")
    gate = np.asarray(gate, dtype=np.complex128).reshape(2, 2)
    out = list(mpo)
    out[slot] = np.einsum("co,lior->licr", gate, out[slot])
    return out


def cx_matrix(control: int, target: int) -> np.ndarray:
    """Return a CX matrix in local basis order (first site, second site)."""
    gate = np.zeros((4, 4), dtype=np.complex128)
    for first in range(2):
        for second in range(2):
            bits = [first, second]
            if bits[control]:
                bits[target] ^= 1
            row = 2 * bits[0] + bits[1]
            col = 2 * first + second
            gate[row, col] = 1.0
    return gate


def u3_matrix(theta: float, phi: float, lam: float) -> np.ndarray:
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.asarray(
        [[c, -np.exp(1j * lam) * s],
         [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]],
        dtype=np.complex128,
    )


def apply_u3_cx_qasm(
    path: str, physical_to_slot: Mapping[int, int], n_sites: int = 12
) -> list[np.ndarray]:
    """Replay standalone u3/cx QASM into an exact MPO accumulator."""
    circuit = qasm2.loads(open(path).read())
    if circuit.num_qubits != n_sites or set(circuit.count_ops()) - {"u3", "cx"}:
        raise ValueError("expected a standalone u3/cx circuit")
    mpo = identity_mpo(n_sites)
    for inst in circuit.data:
        name = inst.operation.name
        if name == "u3":
            physical = circuit.find_bit(inst.qubits[0]).index
            mpo = apply_single_qubit(
                mpo, physical_to_slot[physical], u3_matrix(*map(float, inst.operation.params))
            )
        elif name == "cx":
            control = physical_to_slot[circuit.find_bit(inst.qubits[0]).index]
            target = physical_to_slot[circuit.find_bit(inst.qubits[1]).index]
            if abs(control - target) != 1:
                raise ValueError("QASM CX is not adjacent in the MPO order")
            first = min(control, target)
            mpo = apply_adjacent_gate(mpo, first, cx_matrix(control - first, target - first))
    return mpo


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
