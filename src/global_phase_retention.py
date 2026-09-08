"""Global phase-edge sharing probe across all ten rank terms."""

import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from formula import formula, remap
from xag import Graph
from phase_pebble_rank import CombinedGraph, phase_edges
from phase_retention import execute_actions, greedy_schedule, relevant_nodes, score


def build():
    terms = json.loads(Path("artifacts/rank_mc_pareto_terms.json").read_text())
    x_graph = Graph(); y_graph = Graph()
    x_roots = [x_graph.expr(remap(formula(x, 6), range(6))) for x, _ in terms]
    y_roots_raw = [y_graph.expr(remap(formula(y, 6), range(6, 12))) for _, y in terms]
    y_map = {node: 100 + i for i, node in enumerate(sorted(node for node in y_graph.nodes if node >= 12))}
    nodes = dict(x_graph.nodes)
    for node, (left, right) in y_graph.nodes.items():
        if node >= 12:
            translate = lambda form: frozenset(y_map.get(value, value) for value in form)
            nodes[y_map[node]] = (translate(left), translate(right))
    y_roots = [frozenset(y_map.get(value, value) for value in root) for root in y_roots_raw]
    graph = CombinedGraph(Graph(), Graph()); graph.nodes = nodes
    edges = set(); constant = False
    for x_root, y_root in zip(x_roots, y_roots):
        term_edges, term_constant = phase_edges(x_root, y_root)
        edges.symmetric_difference_update(term_edges); constant ^= term_constant
    return graph, sorted(edges), constant


def main():
    graph, edges, constant = build()
    actions = greedy_schedule(graph, edges, list(range(len(edges))))
    circuit, metrics = execute_actions(graph, edges, actions, constant)
    out = transpile(circuit, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    path = Path("artifacts/global_phase_retention.qasm"); path.write_text(qasm2.dumps(out))
    result = {"nodes": len(relevant_nodes(graph, edges)), "phase_edges": len(edges), "actions": len(actions),
              "depth": out.depth(), "cx": out.count_ops().get("cx", 0), "width": out.num_qubits, **metrics,
              "status": "global edge-sharing probe"}
    Path("artifacts/global_phase_retention_metrics.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
