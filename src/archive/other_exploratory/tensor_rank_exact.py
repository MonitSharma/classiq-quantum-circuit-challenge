"""Exact modular certification of the logo sign tensor TT ranks.

The existing MPO module reports numerical SVD ranks.  This companion audit
uses integer truth-table entries and Gaussian elimination modulo several large
primes.  The modular ranks are lower bounds over characteristic zero; the
matching TT-SVD factorization supplies the corresponding numerical upper bound
and is recorded separately.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sympy as sp

from mpo_target import DEFAULT_ORDER, DIM, N_DATA, ordered_tensor, tt_ranks


PRIMES = (1_000_003, 1_000_033, 1_000_037)


def rank_mod(matrix: np.ndarray, prime: int) -> int:
    """Return the rank of an integer matrix over GF(prime)."""
    a = np.asarray(matrix, dtype=np.int64).copy() % prime
    rows, cols = a.shape
    rank = 0
    for col in range(cols):
        pivot = next((row for row in range(rank, rows) if a[row, col]), None)
        if pivot is None:
            continue
        if pivot != rank:
            a[[rank, pivot]] = a[[pivot, rank]]
        a[rank] = (a[rank] * pow(int(a[rank, col]), -1, prime)) % prime
        other_rows = np.flatnonzero(a[:, col])
        other_rows = other_rows[other_rows != rank]
        if len(other_rows):
            a[other_rows] = (a[other_rows] - a[other_rows, col, None] * a[rank]) % prime
        rank += 1
        if rank == rows:
            break
    return rank


def main() -> dict:
    root = Path(__file__).resolve().parents[1]
    tensor = np.asarray(ordered_tensor(DEFAULT_ORDER), dtype=np.int64)
    signs = tensor.reshape(-1).astype(np.int8)
    ranks = {}
    for cut in range(1, N_DATA):
        unfolding = tensor.reshape(2**cut, 2 ** (N_DATA - cut))
        ranks[str(cut)] = {str(p): rank_mod(unfolding, p) for p in PRIMES}
    modular_profile = [ranks[str(cut)][str(PRIMES[0])] for cut in range(1, N_DATA)]
    if any(len(set(value.values())) != 1 for value in ranks.values()):
        raise AssertionError("modular rank disagreement")
    if modular_profile != tt_ranks(tensor)[1:-1]:
        raise AssertionError("modular and numerical TT profiles disagree")
    # Build an exact rational TT witness using successive exact rank
    # decompositions.  This is small for the 12-bit target and avoids treating
    # the floating-point TT-SVD as an exact upper-bound certificate.
    exact_cores: list[list[list[str]]] = []
    remaining = sp.Matrix(tensor.reshape(2, -1).tolist())
    left_rank = 1
    for axis in range(N_DATA - 1):
        core_matrix, tail = remaining.rank_decomposition()
        rank = core_matrix.cols
        if rank != modular_profile[axis]:
            raise AssertionError((axis, rank, modular_profile[axis]))
        exact_cores.append([[str(core_matrix[row, col]) for col in range(rank)]
                            for row in range(left_rank * DIM)])
        left_rank = rank
        if axis == N_DATA - 2:
            remaining = tail
            break
        rest_dim = 2 ** (N_DATA - axis - 2)
        next_remaining = sp.zeros(rank * DIM, rest_dim)
        for bond in range(rank):
            for physical in range(DIM):
                for rest in range(rest_dim):
                    next_remaining[bond * DIM + physical, rest] = tail[
                        bond, physical * rest_dim + rest
                    ]
        remaining = next_remaining
    if remaining.shape != (left_rank, DIM):
        raise AssertionError(remaining.shape)
    exact_cores.append([
        [str(remaining[row // DIM, row % DIM])] for row in range(left_rank * DIM)
    ])
    exact_witness = {
        "kind": "exact rational TT factorization witness",
        "core_shapes_flattened": [
            [len(core), len(core[0])] for core in exact_cores
        ],
        "cores": exact_cores,
        "convention": "core t is flattened as (left_rank*physical_bit, right_rank); row = left*2+bit",
    }
    # Verify the rational witness against every one of the 4096 tensor entries.
    rational_cores = [
        [[sp.Rational(value) for value in row] for row in core]
        for core in exact_cores
    ]
    for bits in np.ndindex((2,) * N_DATA):
        vector = [sp.Integer(1)]
        for core, bit in zip(rational_cores, bits):
            right_rank = len(core[0])
            vector = [
                sum(vector[left] * core[left * DIM + bit][right]
                    for left in range(len(vector)))
                for right in range(right_rank)
            ]
        expected = int(tensor[bits])
        if vector != [sp.Integer(expected)]:
            raise AssertionError((bits, vector, expected))
    exact_witness["all_4096_entries_reconstructed"] = True
    witness_path = root / "artifacts/unitary_state_space/tensor_tt_exact.json"
    witness_path.parent.mkdir(parents=True, exist_ok=True)
    witness_path.write_text(json.dumps(exact_witness, indent=2) + "\n")
    result = {
        "kind": "exact modular TT-rank certification",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "command": "PYTHONPATH=src .venv/bin/python src/tensor_rank_exact.py",
        "order": list(DEFAULT_ORDER),
        "unfolding_ranks": modular_profile,
        "tt_ranks_endpoint_inclusive": [1, *modular_profile, 1],
        "maximum_bond_dimension": max(modular_profile),
        "primes": list(PRIMES),
        "rank_by_prime": ranks,
        "target_sign_sha256": hashlib.sha256(signs.tobytes()).hexdigest(),
        "interpretation": {
            "modular_rank": "lower bound on characteristic-zero integer rank",
            "matching_tt_profile": "exact rational TT factorization supplies a matching upper bound",
            "unitary_warning": "TT cores are not thereby unitary transitions",
        },
        "exact_witness": "artifacts/unitary_state_space/tensor_tt_exact.json",
    }
    path = root / "artifacts/unitary_state_space/tensor_rank_exact.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
