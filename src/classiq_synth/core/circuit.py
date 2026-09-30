"""Utilities for loading QASM circuits, parsing structures, and extracting metrics."""

import hashlib
from pathlib import Path
from typing import Dict, Any, Union
from qiskit import QuantumCircuit, qasm2


def load_circuit(path_or_str: Union[str, Path]) -> tuple[QuantumCircuit, str, str]:
    """Load a QASM circuit from file path or QASM string.

    Returns:
        (circuit, qasm_source, sha256_hash)
    """
    path = Path(path_or_str)
    if path.exists() and path.is_file():
        source = path.read_text()
    else:
        source = str(path_or_str)

    qc = qasm2.loads(source)
    sha256 = hashlib.sha256(source.encode()).hexdigest()
    return qc, source, sha256


def count_gates(qc: QuantumCircuit) -> Dict[str, int]:
    """Count gate operations in circuit."""
    return dict(qc.count_ops())


def get_circuit_metrics(path_or_circuit: Union[str, Path, QuantumCircuit]) -> Dict[str, Any]:
    """Compute depth, gate counts, width, and operation breakdown."""
    if isinstance(path_or_circuit, QuantumCircuit):
        qc = path_or_circuit
        sha256 = None
    else:
        qc, _, sha256 = load_circuit(path_or_circuit)

    ops = count_gates(qc)
    cx_count = ops.get("cx", 0)
    u3_count = ops.get("u3", 0) + ops.get("u", 0)
    total_gates = len(qc.data)

    res = {
        "width": qc.num_qubits,
        "depth": qc.depth(),
        "total_gates": total_gates,
        "cx_count": cx_count,
        "u3_count": u3_count,
        "ops": ops,
    }
    if sha256:
        res["sha256"] = sha256
    return res
