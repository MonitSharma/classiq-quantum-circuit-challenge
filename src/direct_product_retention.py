"""Retain one product factor while streaming the other factor's phase edges.

This is a one-term phase/state-duality-inspired benchmark.  It keeps all
nonlinear constituents of the x root live while computing and clearing the
nonlinear y constituents needed by each diagonal phase edge.
"""

import json
from collections import deque
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from phase_pebble_rank import ANCILLAS, _phase_edge, make_pair_graph, phase_edges
from phase_retention import legal_actions, relevant_nodes, dependencies


def exact_move_plan(graph, start, target, max_states=1_000_000):
    """Find a reversible pebble path whose final live set is exactly target."""
    start = frozenset(start)
    target = frozenset(target)
    nodes = relevant_nodes(graph, [(value, -1) for value in start | target])
    deps = dependencies(graph, nodes)
    queue = deque([start])
    parent = {start: None}
    action_for = {}
    while queue:
        state = queue.popleft()
        if state == target:
            path = []
            while parent[state] is not None:
                path.append(action_for[state])
                state = parent[state]
            return path[::-1]
        if len(parent) >= max_states:
            raise ValueError("exact retained-set search limit")
        for action in legal_actions(graph, state, nodes, deps):
            updated = set(state)
            if action[0] == "compute":
                updated.add(action[1])
            else:
                updated.remove(action[1])
            updated = frozenset(updated)
            if updated not in parent:
                parent[updated] = state
                action_for[updated] = action
                queue.append(updated)
    raise ValueError(f"no exact retained-set path from {sorted(start)} to {sorted(target)}")


def apply_path(q, graph, path, live, wire):
    for kind, node in path:
        was_live = node in live
        # The value remains live across multiple diagonal phase operations.
        # RCCX's relative phases are therefore not guaranteed to cancel at
        # the point where this node is finally cleared; use exact CCX here.
        left, right = graph.nodes[node]
        from xag import linear
        pre, pivot, other = linear(q, left, right, wire)
        if node in live:
            target = wire.pop(node)
        else:
            free = sorted(set(ANCILLAS) - set(wire.values()))
            if not free:
                raise ValueError("shared six-ancilla pool exhausted")
            target = free[0]
            wire[node] = target
        q.compose(pre, inplace=True)
        if len({pivot, other, target}) != 3:
            raise ValueError(f"overlapping XAG wires for node {node}")
        q.ccx(pivot, other, target)
        q.compose(pre.inverse(), inplace=True)
        if node in live:
            live.remove(node)
        else:
            live.add(node)
        if (kind == "compute") != (not was_live):
            raise AssertionError("planner action/live mismatch")


def build(x_table, y_table, cache):
    graph, x_root, y_root, representation = make_pair_graph(x_table, y_table, cache)
    edges, constant = phase_edges(x_root, y_root)
    edges = sorted(edges)
    q = QuantumCircuit(18)
    live = set()
    wire = {index: index for index in range(12)}
    x_targets = {value for value in x_root if value >= 12}
    all_nodes = relevant_nodes(graph, [(value, -1) for value in x_targets | {
        value for edge in edges for value in edge if value >= 12
    }])
    deps = dependencies(graph, all_nodes)
    actions = {"x_retained": sorted(x_targets), "phase_edges": len(edges),
               "compute": 0, "uncompute": 0, "max_live": 0,
               "representation": representation}

    def move(targets, exact_empty=False):
        path = exact_move_plan(graph, live, set(targets), max_states=1_000_000)
        apply_path(q, graph, path, live, wire)
        actions["compute"] += sum(kind == "compute" for kind, _ in path)
        actions["uncompute"] += sum(kind == "uncompute" for kind, _ in path)
        actions["max_live"] = max(actions["max_live"], len(live))
        return path

    move(x_targets)
    for edge in edges:
        needed = set(x_targets)
        needed.update(value for value in edge if value >= 12)
        move(needed)
        _phase_edge(q, edge, wire)
        move(x_targets)
    move(set(), exact_empty=True)
    if live:
        raise AssertionError(f"retained product did not clean ancillas: {live}")
    if constant:
        q.global_phase += 3.141592653589793
    return q, actions


def main():
    cache = json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    terms = json.loads(Path("artifacts/pair_terms.json").read_text())
    index = 0
    q, metrics = build(*terms[index], cache)
    out = transpile(q, basis_gates=["u3", "cx"],
                    qubits_initially_zero=False, optimization_level=3)
    path = Path("artifacts/direct_product_retention_term0_exact_v2_development.qasm")
    path.write_text(qasm2.dumps(out))
    metrics.update({"term_index": index, "depth": out.depth(),
                    "cx": out.count_ops().get("cx", 0), "width": out.num_qubits,
                    "qasm": str(path)})
    Path("artifacts/direct_product_retention_term0_exact_v2_development.metrics.json").write_text(
        json.dumps(metrics, indent=2)
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
