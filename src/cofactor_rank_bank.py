"""Cofactor/Shannon three-output rank-bank control experiment.

This adapts the repository's generic Shannon/Davio tree emitter to the
six-input, three-output rank factors used by ``rank_batch_ucr``.  The solver
shares cofactors within a bank; the two banks are then coupled by three CZ
edges and uncomputed exactly as a standalone product-phase oracle.

The ``clean`` variant gives each bank no borrowed workspace.  The
``cross_dirty`` variant deliberately offers the other bank's live output
wires as scratch to test whether the emitter's relative-phase actions are
safe on dirty values.  It is an exploratory candidate and must pass the
product verifier before being treated as valid.
"""

from __future__ import annotations

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from qrom_tree import emit, solve


ROOT = Path(__file__).resolve().parents[1]


def output_table(tables: list[int]) -> tuple[int, ...]:
    """Return a 3-bit output code for each six-bit input value."""
    if len(tables) != 3:
        raise ValueError("a rank bank must contain exactly three outputs")
    return tuple(sum(((table >> input_value) & 1) << output
                     for output, table in enumerate(tables))
                 for input_value in range(64))


def bank(tables: list[int], inputs: list[int], outputs: list[int],
         free: list[int]) -> tuple[QuantumCircuit, int]:
    """Compile one three-output bank and return its abstract tree score."""
    table = output_table(tables)
    score, program = solve(table, 6, False, len(free))
    circuit = QuantumCircuit(18)
    emit(circuit, program, inputs, None, list(free), outputs)
    return circuit, score


def build(indices=(0, 1, 2), variant="clean", basis="rank_terms",
          seed=0):
    """Build and serialize-ready compile a three-term product-phase batch."""
    if variant not in {"clean", "cross_dirty"}:
        raise ValueError(f"unknown variant: {variant}")
    terms = json.loads((ROOT / "artifacts" / f"{basis}.json").read_text())
    x_outputs = [terms[index][0] for index in indices]
    y_outputs = [terms[index][1] for index in indices]
    x_scratch = [] if variant == "clean" else [15, 16, 17]
    y_scratch = [] if variant == "clean" else [12, 13, 14]
    x_bank, x_score = bank(x_outputs, list(range(6)), [12, 13, 14], x_scratch)
    y_bank, y_score = bank(y_outputs, list(range(6, 12)), [15, 16, 17], y_scratch)

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
    return compiled, {"x_tree_score": x_score, "y_tree_score": y_score,
                      "x_raw_depth": x_bank.depth(),
                      "y_raw_depth": y_bank.depth()}


def main() -> None:
    for variant in ("clean", "cross_dirty"):
        circuit, extra = build(variant=variant)
        name = f"cofactor_rank_bank_012_{variant}_development"
        qasm_path = ROOT / "artifacts" / f"{name}.qasm"
        qasm_path.write_text(qasm2.dumps(circuit))
        metrics = {
            "indices": [0, 1, 2], "basis": "rank_terms", "variant": variant,
            "depth": circuit.depth(),
            "cx": circuit.count_ops().get("cx", 0),
            "width": circuit.num_qubits, "qasm": str(qasm_path), **extra,
        }
        (ROOT / "artifacts" / f"{name}.metrics.json").write_text(
            json.dumps(metrics, indent=2) + "\n"
        )
        print(json.dumps(metrics, indent=2), flush=True)


if __name__ == "__main__":
    main()
