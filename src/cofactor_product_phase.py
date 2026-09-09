"""Three-term cofactor bank with direct temporary-product phase emission.

The x-side factors are computed together by the Shannon/Davio cofactor
emitter.  Once that bank is live, each y-side Boolean factor is emitted as a
phase ESOP controlled by its corresponding x output.  The y-side functions
are never materialized into a second live bank, and the cofactor scratch
wires are clean before every phase cube.  The x bank is then uncomputed.
"""

from __future__ import annotations

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from factor import phase_cube
from qrom_tree import emit, solve
from search import esop


ROOT = Path(__file__).resolve().parents[1]


def output_table(tables: list[int]) -> tuple[int, ...]:
    return tuple(sum(((table >> input_value) & 1) << output
                     for output, table in enumerate(tables))
                 for input_value in range(64))


def build(indices=(0, 1, 2), basis="rank_terms", seed=0):
    terms = json.loads((ROOT / "artifacts" / f"{basis}.json").read_text())
    x_tables = [terms[index][0] for index in indices]
    y_tables = [terms[index][1] for index in indices]
    table = output_table(x_tables)
    tree_score, program = solve(table, 6, False, 3)
    x_bank = QuantumCircuit(18)
    emit(x_bank, program, list(range(6)), None, [15, 16, 17],
         [12, 13, 14])

    circuit = QuantumCircuit(18)
    circuit.compose(x_bank, inplace=True)
    # q15..q17 (1-based literals 16..18) were scratch during x_bank and are
    # clean here.  Each phase cube restores those helpers before the next one.
    for output, table in enumerate(y_tables):
        for mask, value in esop(table, 6):
            cube = {13 + output}
            for bit in range(6):
                if mask >> bit & 1:
                    literal = 7 + bit
                    cube.add(literal if value >> bit & 1 else -literal)
            phase_cube(circuit, frozenset(cube), [16, 17, 18])
    circuit.compose(x_bank.inverse(), inplace=True)
    compiled = transpile(circuit, basis_gates=["u3", "cx"],
                         qubits_initially_zero=False,
                         optimization_level=3, seed_transpiler=seed)
    return compiled, {"x_tree_score": tree_score,
                      "x_raw_depth": x_bank.depth(),
                      "y_esop_cubes": [len(esop(table, 6))
                                       for table in y_tables]}


def main() -> None:
    circuit, extra = build()
    name = "cofactor_product_phase_012_development"
    qasm_path = ROOT / "artifacts" / f"{name}.qasm"
    qasm_path.write_text(qasm2.dumps(circuit))
    metrics = {"indices": [0, 1, 2], "basis": "rank_terms",
               "depth": circuit.depth(),
               "cx": circuit.count_ops().get("cx", 0),
               "width": circuit.num_qubits, "qasm": str(qasm_path), **extra}
    (ROOT / "artifacts" / f"{name}.metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
