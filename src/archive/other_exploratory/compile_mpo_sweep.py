"""Compile an abstract MPO gate-sweep checkpoint to challenge basis gates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import UnitaryGate

from mpo_target import DEFAULT_ORDER


def load_checkpoint(path: str | Path) -> QuantumCircuit:
    data = np.load(path, allow_pickle=True)
    gates = np.asarray(data["gates"])
    layers = data["layers"].tolist()
    circuit = QuantumCircuit(12)
    position = 0
    for layer in layers:
        for first, second in layer:
            # The abstract tensor convention is (first, second), while the
            # Qiskit local matrix convention follows the supplied qubit list.
            physical = [DEFAULT_ORDER[second], DEFAULT_ORDER[first]]
            circuit.append(UnitaryGate(gates[position]), physical)
            position += 1
    if position != len(gates):
        raise ValueError("checkpoint gate count does not match topology")
    return circuit


def compile_checkpoint(checkpoint: str | Path, output: str | Path) -> dict:
    source = load_checkpoint(checkpoint)
    compiled = transpile(
        source,
        basis_gates=["u3", "cx"],
        optimization_level=3,
        qubits_initially_zero=False,
        seed_transpiler=0,
    )
    qasm = qasm2.dumps(compiled)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(qasm)
    report = {
        "checkpoint": str(Path(checkpoint)),
        "qasm": str(output),
        "sha256": hashlib.sha256(qasm.encode()).hexdigest(),
        "width": compiled.num_qubits,
        "depth": compiled.depth(),
        "cx_count": int(compiled.count_ops().get("cx", 0)),
        "basis": sorted(compiled.count_ops()),
        "promoted": False,
        "reason": "abstract MPO gate-sweep checkpoint; approximate and not exhaustively verified",
    }
    output.with_suffix(".compile.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(compile_checkpoint(args.checkpoint, args.output), indent=2))
