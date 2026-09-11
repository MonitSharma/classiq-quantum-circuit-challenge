"""Bounded pytket post-processing for a phase-history QASM candidate."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from pytket.passes import CliffordSimp, FullPeepholeOptimise
from pytket.qasm import circuit_from_qasm, circuit_to_qasm
from qiskit import QuantumCircuit, qasm2, transpile


def lower(source: Path, pass_type):
    circuit = circuit_from_qasm(str(source))
    pass_type().apply(circuit)
    with tempfile.NamedTemporaryFile(suffix=".qasm") as handle:
        circuit_to_qasm(circuit, handle.name)
        qiskit_circuit = QuantumCircuit.from_qasm_file(handle.name)
    return transpile(
        qiskit_circuit, basis_gates=["u3", "cx"],
        qubits_initially_zero=False, optimization_level=3,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    candidates = [
        ("full_peephole", lower(args.source, FullPeepholeOptimise)),
        ("clifford_simp", lower(args.source, CliffordSimp)),
    ]
    name, best = min(candidates, key=lambda item: (
        item[1].depth(), item[1].count_ops().get("cx", 0)
    ))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(qasm2.dumps(best))
    result = {
        "source": str(args.source),
        "pass": name,
        "qasm": str(args.out),
        "depth": best.depth(),
        "cx_count": best.count_ops().get("cx", 0),
        "width": best.num_qubits,
        "qubits_initially_zero": False,
        "candidates": [
            {"pass": label, "depth": circuit.depth(),
             "cx_count": circuit.count_ops().get("cx", 0),
             "width": circuit.num_qubits}
            for label, circuit in candidates
        ],
    }
    metrics = args.out.with_suffix(".metrics.json")
    metrics.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
