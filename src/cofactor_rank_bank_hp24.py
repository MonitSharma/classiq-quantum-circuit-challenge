"""Cofactor-bank lowering diagnostic using explicit exact HP24 MCXs."""

from __future__ import annotations

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.synthesis import synth_mcx_noaux_hp24

import qrom_tree


ROOT = Path(__file__).resolve().parents[1]


def exact_mcx(circuit, controls, target, scratch):
    count = len(controls)
    if count == 0:
        circuit.x(target)
    elif count == 1:
        circuit.cx(controls[0], target)
    elif count == 2:
        circuit.ccx(*controls, target)
    else:
        sub = synth_mcx_noaux_hp24(count)
        circuit.compose(sub, qubits=list(controls) + [target], inplace=True)


def exact_toggle_outputs(circuit, controls, mask, outputs, free):
    selected = [outputs[i] for i in range(3) if mask >> i & 1]
    if not selected:
        return
    target = selected[0]
    control_qubits = sorted(abs(value) - 1 for value in controls)
    negative = [abs(value) - 1 for value in controls if value < 0]
    if negative:
        circuit.x(negative)
    for other in selected[1:]:
        circuit.cx(target, other)
    exact_mcx(circuit, control_qubits, target, free)
    for other in selected[1:]:
        circuit.cx(target, other)
    if negative:
        circuit.x(negative)


def build(indices=(0, 1, 2), basis="rank_terms", seed=0):
    terms = json.loads((ROOT / "artifacts" / f"{basis}.json").read_text())
    x_tables = [terms[index][0] for index in indices]
    y_tables = [terms[index][1] for index in indices]

    original_mcx = QuantumCircuit.mcx
    original_toggle = qrom_tree.toggle_outputs

    def mcx_method(circuit, control_qubits, target_qubit, ancilla_qubits=None,
                   mode=None):
        exact_mcx(circuit, list(control_qubits), target_qubit, [])

    QuantumCircuit.mcx = mcx_method
    qrom_tree.toggle_outputs = exact_toggle_outputs
    try:
        x_table = tuple(sum(((table >> value) & 1) << output
                            for output, table in enumerate(x_tables))
                        for value in range(64))
        y_table = tuple(sum(((table >> value) & 1) << output
                            for output, table in enumerate(y_tables))
                        for value in range(64))
        x_score, x_program = qrom_tree.solve(x_table, 6, False, 0)
        y_score, y_program = qrom_tree.solve(y_table, 6, False, 0)
        x_bank = QuantumCircuit(18)
        y_bank = QuantumCircuit(18)
        qrom_tree.emit(x_bank, x_program, list(range(6)), None, [],
                       [12, 13, 14])
        qrom_tree.emit(y_bank, y_program, list(range(6, 12)), None, [],
                       [15, 16, 17])
    finally:
        QuantumCircuit.mcx = original_mcx
        qrom_tree.toggle_outputs = original_toggle

    circuit = QuantumCircuit(18)
    circuit.compose(x_bank, inplace=True)
    circuit.compose(y_bank, inplace=True)
    for x_wire, y_wire in zip((12, 13, 14), (15, 16, 17)):
        circuit.cz(x_wire, y_wire)
    circuit.compose(y_bank.inverse(), inplace=True)
    circuit.compose(x_bank.inverse(), inplace=True)
    compiled = transpile(circuit, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False,
                         optimization_level=3, seed_transpiler=seed)
    return compiled, {"indices": list(indices), "basis": basis,
                      "x_tree_score": x_score, "y_tree_score": y_score,
                      "depth": compiled.depth(),
                      "cx": compiled.count_ops().get("cx", 0),
                      "width": compiled.num_qubits}


def main():
    circuit, metrics = build()
    name = "cofactor_rank_bank_012_hp24_development"
    path = ROOT / "artifacts" / f"{name}.qasm"
    path.write_text(qasm2.dumps(circuit))
    metrics["qasm"] = str(path)
    (ROOT / "artifacts" / f"{name}.metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
