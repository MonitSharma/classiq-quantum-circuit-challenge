"""Compile the extracted global phase edges with the existing pair compiler."""

from __future__ import annotations

import json
import random
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from pair_search import pair_circuit


def compile_order(blocks, order):
    circuit = QuantumCircuit(18)
    for index in order:
        circuit.compose(blocks[index], inplace=True)
    return transpile(circuit, basis_gates=["u3", "cx"],
                     optimization_level=3, qubits_initially_zero=False)


def main(trials=100):
    payload = json.loads(Path("artifacts/global_12_edge_endpoints.json").read_text())
    edges = [(row["x_truth_table"], row["y_truth_table"]) for row in payload["edges"]]
    blocks = [pair_circuit(x, y) for x, y in edges]
    orders = [list(range(len(blocks))), list(reversed(range(len(blocks))))]
    rng = random.Random(20260910)
    orders.extend(rng.sample(range(len(blocks)), len(blocks)) for _ in range(trials))
    rows = []
    best = None
    best_qasm = None
    for index, order in enumerate(orders):
        out = compile_order(blocks, order)
        row = {"trial": index, "order": list(order), "depth": out.depth(),
               "cx": out.count_ops().get("cx", 0), "width": out.num_qubits}
        rows.append(row)
        if best is None or (row["depth"], row["cx"]) < (best["depth"], best["cx"]):
            best, best_qasm = row, out
    Path("artifacts/global_endpoint_pair_search.json").write_text(
        json.dumps({"results": rows, "best": best}, indent=2))
    Path("artifacts/global_endpoint_pair_best.qasm").write_text(qasm2.dumps(best_qasm))
    print(json.dumps(best, indent=2))


if __name__ == "__main__":
    main()
