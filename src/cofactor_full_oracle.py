"""Complete-logo integration of the cofactor temporary-product phase pilot."""

from __future__ import annotations

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from factor import phase_cube
from qrom_tree import emit, solve
from search import esop


ROOT = Path(__file__).resolve().parents[1]
GROUPS = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (9,))


def output_table(tables):
    return tuple(sum(((table >> value) & 1) << output
                     for output, table in enumerate(tables))
                 for value in range(64))


def group_circuit(terms, indices):
    """Return an uncompiled, ancilla-clean phase circuit for one group."""
    x_tables = [terms[index][0] for index in indices]
    y_tables = [terms[index][1] for index in indices]
    while len(x_tables) < 3:
        x_tables.append(0)
        y_tables.append(0)
    score, program = solve(output_table(x_tables), 6, False, 3)
    x_bank = QuantumCircuit(18)
    emit(x_bank, program, list(range(6)), None, [15, 16, 17],
         [12, 13, 14])
    circuit = QuantumCircuit(18)
    circuit.compose(x_bank, inplace=True)
    for output, table in enumerate(y_tables):
        if indices and output >= len(indices):
            continue
        for mask, value in esop(table, 6):
            cube = {13 + output}
            for bit in range(6):
                if mask >> bit & 1:
                    literal = 7 + bit
                    cube.add(literal if value >> bit & 1 else -literal)
            phase_cube(circuit, frozenset(cube), [16, 17, 18])
    circuit.compose(x_bank.inverse(), inplace=True)
    return circuit, score


def build(seed=0, basis="rank_terms"):
    terms = json.loads((ROOT / "artifacts" / f"{basis}.json").read_text())
    circuit = QuantumCircuit(18)
    scores = []
    for indices in GROUPS:
        group, score = group_circuit(terms, indices)
        circuit.compose(group, inplace=True)
        scores.append({"indices": list(indices), "tree_score": score,
                       "raw_depth": group.depth()})
    compiled = transpile(circuit, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False,
                         optimization_level=3, seed_transpiler=seed)
    return compiled, scores


def main():
    circuit, groups = build()
    name = "cofactor_full_rank_phase_development"
    qasm_path = ROOT / "artifacts" / f"{name}.qasm"
    qasm_path.write_text(qasm2.dumps(circuit))
    metrics = {"groups": groups, "depth": circuit.depth(),
               "cx": circuit.count_ops().get("cx", 0),
               "width": circuit.num_qubits, "qasm": str(qasm_path)}
    (ROOT / "artifacts" / f"{name}.metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
