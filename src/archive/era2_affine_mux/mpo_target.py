"""Exact tensor-train/MPO representation of the Classiq logo phase oracle.

This module is deliberately independent of circuit synthesis.  It constructs
the sign tensor directly from ``search.logo``, computes exact numerical TT
ranks using TT-SVD, reconstructs the tensor, and exposes the corresponding
diagonal MPO cores.  The tensor-network axis order is explicit because the
challenge's qubits are little-endian while a useful TT order is not.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from search import logo


DEFAULT_ORDER = (0, 1, 2, 3, 4, 5, 11, 8, 6, 7, 9, 10)
N_DATA = 12
DIM = 2


def challenge_sign_table() -> np.ndarray:
    """Return signs in challenge basis order: y-major, x-fastest."""
    return np.asarray(
        [(-1 if logo(x, y) else 1) for y in range(64) for x in range(64)],
        dtype=np.int8,
    )


def ordered_tensor(order: Sequence[int] = DEFAULT_ORDER) -> np.ndarray:
    """Return ``S`` with axes arranged according to physical qubit numbers.

    Axis ``i`` is the computational bit of physical qubit ``order[i]``.  The
    returned tensor therefore has shape ``(2,)*12`` and is independent of
    NumPy's native flattening convention.
    """
    order = tuple(order)
    if sorted(order) != list(range(N_DATA)):
        raise ValueError(f"order must be a permutation of 0..11, got {order}")
    out = np.empty((DIM,) * N_DATA, dtype=np.int8)
    for bits in np.ndindex(out.shape):
        physical = [0] * N_DATA
        for axis, bit in enumerate(bits):
            physical[order[axis]] = bit
        x = sum(physical[i] << i for i in range(6))
        y = sum(physical[6 + i] << i for i in range(6))
        out[bits] = -1 if logo(x, y) else 1
    return out


def _numerical_rank(matrix: np.ndarray, rtol: float) -> int:
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    if not len(singular_values):
        return 0
    cutoff = rtol * max(matrix.shape) * singular_values[0]
    return int(np.count_nonzero(singular_values > cutoff))


def tt_ranks(tensor: np.ndarray, rtol: float = 1e-12) -> list[int]:
    """Return endpoint-inclusive TT ranks from successive matricizations."""
    if tensor.ndim != N_DATA or any(size != DIM for size in tensor.shape):
        raise ValueError("expected a 12-axis binary tensor")
    ranks = [1]
    for cut in range(1, tensor.ndim):
        matrix = tensor.reshape(2**cut, -1)
        ranks.append(_numerical_rank(matrix, rtol))
    ranks.append(1)
    return ranks


def tt_svd(tensor: np.ndarray, rtol: float = 1e-12) -> tuple[list[np.ndarray], list[int]]:
    """Compute a deterministic exact-to-tolerance TT decomposition.

    Each core has shape ``(left_rank, physical_dimension, right_rank)``.
    No truncation is performed beyond dropping singular values below the
    supplied numerical threshold.
    """
    work = np.asarray(tensor, dtype=np.float64)
    cores: list[np.ndarray] = []
    left_rank = 1
    remaining = work
    for axis in range(N_DATA - 1):
        matrix = remaining.reshape(left_rank * DIM, -1)
        u, singular_values, vh = np.linalg.svd(matrix, full_matrices=False)
        cutoff = rtol * max(matrix.shape) * singular_values[0]
        rank = int(np.count_nonzero(singular_values > cutoff))
        if rank == 0:
            raise RuntimeError(f"zero TT rank at cut {axis + 1}")
        cores.append(u[:, :rank].reshape(left_rank, DIM, rank))
        # ``remaining`` has a leading bond axis after the first split.  Each
        # later split consumes that bond axis and the next physical axis.
        tail_shape = remaining.shape[1:] if axis == 0 else remaining.shape[2:]
        remaining = (singular_values[:rank, None] * vh[:rank]).reshape(
            (rank,) + tail_shape
        )
        left_rank = rank
    cores.append(remaining.reshape(left_rank, DIM, 1))
    return cores, [core.shape[0] for core in cores] + [1]


def reconstruct_tt(cores: Sequence[np.ndarray]) -> np.ndarray:
    """Reconstruct a tensor from cores shaped ``(left, physical, right)``."""
    if len(cores) != N_DATA:
        raise ValueError(f"expected {N_DATA} cores")
    result = np.asarray(cores[0], dtype=np.float64)
    for core in cores[1:]:
        result = np.tensordot(result, core, axes=(-1, 0))
    return np.squeeze(result, axis=(0, -1))


def diagonal_mpo(cores: Sequence[np.ndarray]) -> list[np.ndarray]:
    """Attach input/output physical indices to TT cores.

    The returned core shape is ``(left, right, input_bit, output_bit)`` and
    contains ``TT_core[..., bit] * delta(input_bit, output_bit)``.  This is an
    exact diagonal MPO, not a circuit approximation.
    """
    mpo = []
    for core in cores:
        out = np.zeros((core.shape[0], core.shape[2], DIM, DIM), dtype=core.dtype)
        for bit in range(DIM):
            out[:, :, bit, bit] = core[:, bit, :]
        mpo.append(out)
    return mpo


def mpo_basis_action(mpo: Sequence[np.ndarray], bits: Sequence[int]) -> float:
    """Evaluate the diagonal MPO coefficient for one ordered basis string."""
    if len(mpo) != N_DATA or len(bits) != N_DATA:
        raise ValueError("expected 12 MPO cores and 12 bits")
    vec = np.ones((1,), dtype=np.float64)
    for core, bit in zip(mpo, bits):
        vec = np.tensordot(vec, core[:, :, bit, bit], axes=(-1, 0))
    return float(np.squeeze(vec))


def target_hash(signs: np.ndarray | None = None) -> str:
    if signs is None:
        signs = challenge_sign_table()
    return hashlib.sha256(np.asarray(signs, dtype=np.int8).tobytes()).hexdigest()


def _save_cores(path: Path, cores: Sequence[np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **{f"core_{i:02d}": core for i, core in enumerate(cores)})


def analyze(order: Sequence[int] = DEFAULT_ORDER, output_dir: str | Path = "artifacts/mpo_native") -> dict:
    output_dir = Path(output_dir)
    signs = challenge_sign_table()
    tensor = ordered_tensor(order)
    cores, decomposition_ranks = tt_svd(tensor)
    reconstructed = reconstruct_tt(cores)
    mpo = diagonal_mpo(cores)

    xy_matrix = signs.reshape(64, 64).astype(np.float64)
    xy_singular_values = np.linalg.svd(xy_matrix, compute_uv=False)
    alternative_orders = {
        "challenge_order": tuple(range(N_DATA)),
        "reverse_order": tuple(reversed(range(N_DATA))),
    }

    marked = int(np.count_nonzero(signs == -1))
    max_reconstruction_error = float(np.max(np.abs(reconstructed - tensor)))
    max_mpo_error = 0.0
    for bits in np.ndindex((2,) * N_DATA):
        value = mpo_basis_action(mpo, bits)
        physical = [0] * N_DATA
        for axis, bit in enumerate(bits):
            physical[order[axis]] = bit
        x = sum(physical[i] << i for i in range(6))
        y = sum(physical[6 + i] << i for i in range(6))
        expected = -1.0 if logo(x, y) else 1.0
        max_mpo_error = max(max_mpo_error, abs(value - expected))

    _save_cores(output_dir / "target_tt.npz", cores)
    # The diagonal MPO is small enough to save as separate cores and is useful
    # to downstream contractions without materializing a 4096x4096 matrix.
    _save_cores(output_dir / "target_mpo.npz", diagonal_mpo(cores))
    report = {
        "order": list(order),
        "marked_states": marked,
        "total_states": int(signs.size),
        "target_sha256": target_hash(signs),
        "tt_ranks": tt_ranks(tensor),
        "decomposition_ranks": decomposition_ranks,
        "max_reconstruction_error": max_reconstruction_error,
        "max_mpo_basis_action_error": max_mpo_error,
        "tensor_dtype": str(tensor.dtype),
        "decomposition_dtype": str(cores[0].dtype),
        "representation": "diagonal MPO from exact TT sign tensor",
        "x_y_matrix_rank": int(np.linalg.matrix_rank(xy_matrix)),
        "x_y_singular_values": [float(value) for value in xy_singular_values],
        "alternative_tt_ranks": {
            name: tt_ranks(ordered_tensor(candidate_order))
            for name, candidate_order in alternative_orders.items()
        },
    }
    (output_dir / "structural_report.json").write_text(json.dumps(report, indent=2) + "\n")
    np.save(output_dir / "target_signs.npy", signs)
    return report


if __name__ == "__main__":
    print(json.dumps(analyze(), indent=2))
