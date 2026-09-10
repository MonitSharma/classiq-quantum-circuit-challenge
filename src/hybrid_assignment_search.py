"""Reproducible mixed compiler-assignment and term-order search."""

import json
import random
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile


def main(trials=500):
    rows = json.loads(Path("artifacts/rank_portfolio_metrics.json").read_text())
    choices = [[c for c in row["candidates"] if "depth" in c] for row in rows]
    rng = random.Random(20260910); results = []; best = None; best_q = None
    for trial in range(trials):
        assignment = [rng.choice(group) for group in choices]
        order = list(range(10)); rng.shuffle(order); q = QuantumCircuit(18)
        for index in order: q.compose(QuantumCircuit.from_qasm_file(assignment[index]["qasm"]), inplace=True)
        out = transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
        row = {"trial": trial, "order": order, "assignment": [c["compiler"] for c in assignment],
               "depth": out.depth(), "cx": out.count_ops().get("cx", 0)}
        results.append(row)
        if best is None or (row["depth"], row["cx"]) < (best["depth"], best["cx"]): best, best_q = row, out
    Path("artifacts/hybrid_rank_assignment_search.json").write_text(json.dumps({"results": results, "best": best}, indent=2))
    Path("artifacts/hybrid_rank_best_mixed.qasm").write_text(qasm2.dumps(best_q))
    print(json.dumps(best, indent=2))


if __name__ == "__main__": main()
