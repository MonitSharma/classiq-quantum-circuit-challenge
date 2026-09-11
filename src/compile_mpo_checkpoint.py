"""Compile a non-promoted MPO optimizer checkpoint to the challenge basis."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import UnitaryGate

from mpo_target import DEFAULT_ORDER


def layer_pairs(parity: bool) -> list[tuple[int, int]]:
    slots = list(range(12)) if parity else list(range(1, 11))
    return list(zip(slots[::2], slots[1::2]))


def load_checkpoint(path: str | Path) -> QuantumCircuit:
    gates = np.load(path)["gates"]
    if gates.shape != (22, 4, 4):
        raise ValueError("expected a 4-layer checkpoint with 22 SU(4) gates")
    circuit = QuantumCircuit(12)
    pos = 0
    for parity in (True, False, True, False):
        for slot, gate in zip(layer_pairs(parity), gates[pos : pos + len(layer_pairs(parity))]):
            # Qiskit's two-qubit matrix factors are ordered opposite to the
            # TT slot convention used by the MPO contraction.
            physical = [DEFAULT_ORDER[slot[1]], DEFAULT_ORDER[slot[0]]]
            circuit.append(UnitaryGate(gate), physical)
            pos += 1
    return circuit


def compile_checkpoint(
    checkpoint: str | Path, output: str | Path, abstract_report: str | Path | None = None
) -> dict:
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
    source_report = Path(abstract_report) if abstract_report else Path(checkpoint).with_suffix(".json")
    abstract_fidelity = None
    if source_report.exists():
        try:
            abstract_fidelity = json.loads(source_report.read_text()).get("final_process_fidelity")
        except (OSError, json.JSONDecodeError):
            pass
    report = {
        "checkpoint": str(Path(checkpoint)),
        "qasm": str(output),
        "sha256": hashlib.sha256(qasm.encode()).hexdigest(),
        "width": compiled.num_qubits,
        "depth": compiled.depth(),
        "cx_count": int(compiled.count_ops().get("cx", 0)),
        "abstract_process_fidelity": abstract_fidelity,
        "compiled_process_fidelity": None,
        "compiled_fidelity_note": "deferred to the exact promotion pipeline; Qiskit transpilation preserves the unitary by construction",
        "promoted": False,
        "reason": "abstract checkpoint is approximate and has not passed exhaustive oracle verification",
    }
    output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    parser.add_argument("output")
    parser.add_argument("--abstract-report")
    args = parser.parse_args()
    print(
        json.dumps(
            compile_checkpoint(args.checkpoint, args.output, args.abstract_report), indent=2
        )
    )
