"""Exact operator-level diagnostics for MPO-native circuit experiments.

The dense path is intentionally a smoke-test and promotion diagnostic, not the
eventual optimizer.  It is useful because it makes the process objective
unambiguous before introducing tensor-network contractions.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from qiskit.circuit.library import UnitaryGate
from scipy.stats import unitary_group

from mpo_target import challenge_sign_table
from mpo_topologies import N_QUBITS, round_robin_matchings


DIM = 1 << N_QUBITS


def process_metrics(circuit: QuantumCircuit) -> dict[str, float]:
    """Evaluate full-operator metrics for a 12-qubit circuit.

    The target is diagonal, so the process overlap only needs the candidate
    diagonal.  The candidate matrix is still formed here so off-diagonal
    leakage is measured rather than silently ignored.
    """
    if circuit.num_qubits != N_QUBITS:
        raise ValueError("dense smoke objective expects exactly 12 qubits")
    candidate = np.asarray(Operator(circuit).data)
    signs = challenge_sign_table().astype(np.complex128)
    diagonal = np.diag(candidate)
    overlap = np.vdot(signs, diagonal)
    process_fidelity = float(abs(overlap) ** 2 / DIM**2)
    phase = overlap / abs(overlap) if abs(overlap) else 1.0 + 0.0j
    diagonal_error = float(np.linalg.norm(diagonal - phase * signs) / np.sqrt(DIM))
    total_norm_sq = float(np.sum(np.abs(candidate) ** 2))
    off_diagonal_norm = float(
        np.sqrt(max(0.0, total_norm_sq - np.sum(np.abs(diagonal) ** 2))) / np.sqrt(DIM)
    )
    return {
        "process_fidelity": process_fidelity,
        "process_infidelity": 1.0 - process_fidelity,
        "global_phase_real": float(np.real(phase)),
        "global_phase_imag": float(np.imag(phase)),
        "global_phase_aligned_diagonal_error": diagonal_error,
        "normalized_off_diagonal_frobenius": off_diagonal_norm,
    }


def random_matching_layer(seed: int = 0) -> QuantumCircuit:
    """Create one random six-gate layer for an objective smoke test."""
    rng = np.random.default_rng(seed)
    circuit = QuantumCircuit(N_QUBITS)
    for pair in round_robin_matchings()[seed % 11]:
        gate = unitary_group.rvs(4, random_state=rng)
        circuit.append(UnitaryGate(gate), list(pair))
    return circuit


def run_smoke(output: str | Path = "artifacts/mpo_native/objective_smoke.jsonl") -> list[dict]:
    """Record identity and one random matching-layer objective baselines."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    identity = QuantumCircuit(N_QUBITS)
    rows.append({"case": "identity", "layers": 0, **process_metrics(identity)})
    random_layer = random_matching_layer(0)
    rows.append({"case": "random_matching_layer", "layers": 1, **process_metrics(random_layer)})
    output.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    return rows


if __name__ == "__main__":
    print(json.dumps(run_smoke(), indent=2))
