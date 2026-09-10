"""Compile the rank-10 factorization derived from global endpoints."""

import json
import random
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from pair_search import pair_circuit


def main(trials=50):
    terms = json.loads(Path("artifacts/global_endpoint_rank_terms.json").read_text())["terms"]
    blocks = [pair_circuit(t["x_truth_table"], t["y_truth_table"]) for t in terms]
    rng = random.Random(20260910)
    orders = [list(range(len(blocks))), list(reversed(range(len(blocks))))]
    orders += [rng.sample(range(len(blocks)), len(blocks)) for _ in range(trials)]
    best = None; best_q = None; rows = []
    for i, order in enumerate(orders):
        q = QuantumCircuit(18)
        for j in order: q.compose(blocks[j], inplace=True)
        out = transpile(q, basis_gates=["u3", "cx"], optimization_level=3,
                        qubits_initially_zero=False)
        row = {"trial": i, "order": order, "depth": out.depth(),
               "cx": out.count_ops().get("cx", 0), "width": out.num_qubits}
        rows.append(row)
        if best is None or (row["depth"], row["cx"]) < (best["depth"], best["cx"]):
            best, best_q = row, out
    Path("artifacts/global_endpoint_rank_search.json").write_text(json.dumps({"results": rows, "best": best}, indent=2))
    Path("artifacts/global_endpoint_rank_best.qasm").write_text(qasm2.dumps(best_q))
    print(json.dumps(best, indent=2))


if __name__ == "__main__": main()
