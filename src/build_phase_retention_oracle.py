"""Reproduce the committed retained-oracle QASM from committed schedules."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from phase_retention import execute_actions, make_pair_graph, phase_edges


def build(path="artifacts/phase_retention_rank_mc_ordered.qasm", order=None):
    terms = json.loads(Path("artifacts/rank_mc_pareto_terms.json").read_text())
    cache = json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    schedules = json.loads(Path("artifacts/phase_retention_schedules.json").read_text())
    if order is None:
        order = json.loads(Path("artifacts/phase_retention_order_search.json").read_text())["best"]["order"]
    q = QuantumCircuit(18)
    for index in order:
        x, y = terms[index]
        graph, x_root, y_root, _ = make_pair_graph(x, y, cache)
        edges, constant = phase_edges(x_root, y_root)
        actions = [tuple(action) for action in schedules[str(index)]["actions"]]
        pair, _ = execute_actions(graph, sorted(edges), actions, constant)
        q.compose(pair, inplace=True)
    out = transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    Path(path).write_text(qasm2.dumps(out))
    return out


if __name__ == "__main__":
    out = build()
    print({"depth": out.depth(), "cx": out.count_ops().get("cx", 0), "width": out.num_qubits})
