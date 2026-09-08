"""Dynamic phase-edge retention search over a shared six-ancilla pool.

This is the second-stage compiler following :mod:`phase_pebble_rank`.  It
retains nonlinear XAG values while several commuting phase edges are
available, rather than clearing after every edge.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import deque
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from phase_pebble_rank import ANCILLAS, _phase_edge, _toggle, make_pair_graph, phase_edges


def dependencies(graph, nodes):
    return {node: {value for form in graph.nodes[node] for value in form if value >= 12}
            for node in nodes}


def relevant_nodes(graph, edges):
    roots = {value for edge in edges for value in edge if value >= 12}
    out = set(roots)
    stack = list(roots)
    while stack:
        node = stack.pop()
        for form in graph.nodes[node]:
            for value in form:
                if value >= 12 and value not in out:
                    out.add(value)
                    stack.append(value)
    return out


def edge_available(edge, live):
    return (edge[0] < 12 or edge[0] in live) and (edge[1] < 12 or edge[1] in live)


def available_mask(edges, live):
    mask = 0
    for index, edge in enumerate(edges):
        if edge_available(edge, live):
            mask |= 1 << index
    return mask


def legal_actions(graph, live, nodes, deps):
    """Yield reversible-pebble compute/uncompute actions.

    A live child does not forbid clearing its parent: the parent can be
    recomputed before the child is cleared.  This is the standard reversible
    pebble rule and is necessary to use six wires for two deep side graphs.
    """
    live = set(live)
    for node in sorted(nodes):
        if node not in live and deps[node] <= live and len(live) < 6:
            yield ("compute", node)
        elif node in live and deps[node] <= live:
            yield ("uncompute", node)


def move_plan(graph, start, targets, *, exact_empty=False, max_states=1_000_000):
    """Find a legal pooled-pebble path to make targets live or clear all."""
    start = frozenset(start)
    targets = frozenset(targets)
    # Include the complete ancestor closure of both the requested targets and
    # the current live set.  Cleanup may need to recompute a missing parent
    # before it can legally clear a retained child.
    nodes = (relevant_nodes(graph, [(node, -1) for node in targets])
             | relevant_nodes(graph, [(node, -1) for node in start]))
    deps = dependencies(graph, nodes)
    queue = deque([start])
    parent = {start: None}
    action_for = {}
    while queue:
        state = queue.popleft()
        goal = state == frozenset() if exact_empty else targets <= state
        if goal:
            path = []
            while parent[state] is not None:
                path.append(action_for[state])
                state = parent[state]
            return path[::-1]
        if len(parent) >= max_states:
            raise ValueError("retention transition search limit")
        for action in legal_actions(graph, state, nodes, deps):
            next_state = set(state)
            if action[0] == "compute":
                next_state.add(action[1])
            else:
                next_state.remove(action[1])
            next_state = frozenset(next_state)
            if next_state not in parent:
                parent[next_state] = state
                action_for[next_state] = action
                queue.append(next_state)
    raise ValueError("no legal pooled-pebble path")


def structure(x_table, y_table, cache):
    graph, x_root, y_root, representation = make_pair_graph(x_table, y_table, cache)
    edges, constant = phase_edges(x_root, y_root)
    edges = sorted(edges)
    nodes = sorted(relevant_nodes(graph, edges))
    deps = dependencies(graph, nodes)
    return {
        "representation": representation,
        "x_root_constituents": sorted(x_root),
        "y_root_constituents": sorted(y_root),
        "affine_x_root_constituents": sorted(v for v in x_root if v < 12),
        "affine_y_root_constituents": sorted(v for v in y_root if v < 12),
        "nonlinear_x_root_constituents": sorted(v for v in x_root if v >= 12 and v < 100),
        "nonlinear_y_root_constituents": sorted(v for v in y_root if v >= 100),
        "nodes": nodes,
        "dependencies": {str(node): sorted(deps[node]) for node in nodes},
        "phase_edges": [list(edge) for edge in edges],
        "constant_phase": constant,
        "edge_ancestor_closure": {
            str(index): sorted(relevant_nodes(graph, [edge])) for index, edge in enumerate(edges)
        },
    }


def execute_actions(graph, edges, actions, constant=False):
    q = QuantumCircuit(18)
    live = set()
    wire = {index: index for index in range(12)}
    emitted = set()
    metrics = {"compute_actions": 0, "uncompute_actions": 0, "phase_actions": 0,
               "max_live_ancillas": 0}
    for index, edge in enumerate(edges):
        if edge_available(edge, live):
            _phase_edge(q, edge, wire)
            emitted.add(index)
            metrics["phase_actions"] += 1
    for kind, node in actions:
        was_live = node in live
        _toggle(q, graph, node, live, wire)
        if kind == "compute" and was_live or kind == "uncompute" and not was_live:
            raise AssertionError("action/live mismatch")
        metrics["compute_actions" if kind == "compute" else "uncompute_actions"] += 1
        metrics["max_live_ancillas"] = max(metrics["max_live_ancillas"], len(live))
        for index, edge in enumerate(edges):
            if index not in emitted and edge_available(edge, live):
                _phase_edge(q, edge, wire)
                emitted.add(index)
                metrics["phase_actions"] += 1
    if constant:
        q.global_phase += 3.141592653589793
    if live or len(emitted) != len(edges):
        raise AssertionError(f"incomplete schedule live={live} emitted={len(emitted)}/{len(edges)}")
    return q, metrics


def greedy_schedule(graph, edges, order):
    live = set()
    actions = []
    emitted = {index for index, edge in enumerate(edges) if edge_available(edge, live)}
    for index in order:
        edge = edges[index]
        needed = {value for value in edge if value >= 12}
        if not needed <= live:
            path = move_plan(graph, live, needed)
            for action in path:
                actions.append(action)
                if action[0] == "compute":
                    live.add(action[1])
                else:
                    live.remove(action[1])
                for edge_index, candidate in enumerate(edges):
                    if edge_index not in emitted and edge_available(candidate, live):
                        emitted.add(edge_index)
    cleanup = move_plan(graph, live, set(), exact_empty=True)
    actions.extend(cleanup)
    return actions


def order_seeds(edges):
    row = sorted(range(len(edges)), key=lambda i: (edges[i][0], edges[i][1]))
    col = sorted(range(len(edges)), key=lambda i: (edges[i][1], edges[i][0]))
    counts = {}
    for index, edge in enumerate(edges):
        for endpoint in edge:
            if endpoint >= 12:
                counts[endpoint] = counts.get(endpoint, 0) + 1
    shared = sorted(range(len(edges)), key=lambda i: -sum(counts.get(v, 0) for v in edges[i]))
    cheap = sorted(range(len(edges)), key=lambda i: sum(v >= 12 for v in edges[i]))
    expensive = sorted(range(len(edges)), key=lambda i: -sum(counts.get(v, 0) for v in edges[i]))
    return {"row_major": row, "column_major": col, "most_shared": shared,
            "cheapest": cheap, "retention_first": expensive}


def beam_schedule(graph, edges, width, max_steps=300):
    nodes = relevant_nodes(graph, edges)
    deps = dependencies(graph, nodes)
    full = (1 << len(edges)) - 1
    # state: (live frozenset, emitted mask), with path and structural cost.
    beam = {(frozenset(), 0): (0, 0, [])}
    best = None
    for _ in range(max_steps):
        next_states = {}
        for (live, mask), (g, _, path) in beam.items():
            if mask == full:
                try:
                    cleanup = move_plan(graph, live, set(), exact_empty=True)
                    candidate = (g + len(cleanup), path + cleanup)
                    if best is None or candidate[0] < best[0]:
                        best = candidate
                except ValueError:
                    pass
            for kind, node in legal_actions(graph, live, nodes, deps):
                new_live = set(live)
                new_live.add(node) if kind == "compute" else new_live.remove(node)
                new_live = frozenset(new_live)
                new_mask = mask | available_mask(edges, new_live)
                new_g = g + 1
                remaining = len(edges) - new_mask.bit_count()
                # Value only future reuse: emitted edges must not influence
                # the heuristic.  Live endpoints with many remaining
                # incident edges are worth retaining, weighted by the cost of
                # recreating their ancestor closure.
                remaining_edges = [edges[i] for i in range(len(edges)) if not (new_mask >> i) & 1]
                reuse = sum(sum(1 for edge in remaining_edges if node in edge) for node in new_live)
                ancestor_cost = sum(len(relevant_nodes(graph, [(node, -1)])) for node in new_live)
                h = 5 * remaining + 0.1 * len(new_live) + 0.02 * ancestor_cost - 0.5 * reuse
                f = new_g + h
                key = (new_live, new_mask)
                old = next_states.get(key)
                if old is None or f < old[1]:
                    next_states[key] = (new_g, f, path + [(kind, node)])
        if not next_states:
            break
        chosen = sorted(next_states.items(), key=lambda item: item[1][1])[:width]
        beam = {key: value for key, value in chosen}
    if best is None:
        raise ValueError(f"beam-{width} found no complete schedule")
    return best[1]


def score(q):
    out = transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    return out.depth(), out.count_ops().get("cx", 0)


def optimize_term(x_table, y_table, cache, *, local_trials, beam_widths):
    graph, x_root, y_root, representation = make_pair_graph(x_table, y_table, cache)
    edges, constant = phase_edges(x_root, y_root)
    edges = sorted(edges)
    candidates = []
    for name, order in order_seeds(edges).items():
        try:
            actions = greedy_schedule(graph, edges, order)
            q, metrics = execute_actions(graph, edges, actions, constant)
            depth, cx = score(q)
            candidates.append({"scheduler": "greedy_" + name, "actions": actions,
                               "depth": depth, "cx": cx, **metrics})
        except ValueError:
            continue
    rng = random.Random(20260909 + len(edges))
    base = list(range(len(edges)))
    trials = local_trials
    for trial in range(trials):
        order = base[:]
        rng.shuffle(order)
        try:
            actions = greedy_schedule(graph, edges, order)
            # Structural screening first; compile only periodic/best-like
            # candidates to keep the required order search bounded.
            structural = len(actions)
            if trial % max(1, trials // 20) == 0 or structural < min((len(c["actions"]) for c in candidates), default=10**9):
                q, metrics = execute_actions(graph, edges, actions, constant)
                depth, cx = score(q)
                candidates.append({"scheduler": "local_order", "trial": trial,
                                   "actions": actions, "structural_cost": structural,
                                   "depth": depth, "cx": cx, **metrics})
        except ValueError:
            continue
    for width in beam_widths:
        try:
            actions = beam_schedule(graph, edges, width)
            q, metrics = execute_actions(graph, edges, actions, constant)
            depth, cx = score(q)
            candidates.append({"scheduler": f"beam_{width}", "actions": actions,
                               "depth": depth, "cx": cx, **metrics})
        except ValueError as error:
            candidates.append({"scheduler": f"beam_{width}", "error": str(error)})
    complete = [candidate for candidate in candidates if "depth" in candidate]
    if not complete:
        raise ValueError("no complete retention schedule")
    best = min(complete, key=lambda c: (c["depth"], c["cx"], len(c["actions"])))
    best["representation"] = representation
    best["edge_count"] = len(edges)
    best["x_root_constituents"] = len(x_root)
    best["y_root_constituents"] = len(y_root)
    # Do not retain full action lists in the public metric row except for the
    # selected schedule, which is needed to assemble the complete oracle.
    return graph, edges, constant, best, candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-trials-term6", type=int, default=500)
    parser.add_argument("--local-trials-term7", type=int, default=2000)
    args = parser.parse_args()
    cache = json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    terms = json.loads(Path("artifacts/rank_mc_pareto_terms.json").read_text())
    old_rows = json.loads(Path("artifacts/phase_pebble_pair_metrics.json").read_text())["rank_mc_pareto_terms"]
    structure_rows = []
    for index, (x_table, y_table) in enumerate(terms):
        row = {"term_index": index, "x_table": x_table, "y_table": y_table}
        try:
            row.update(structure(x_table, y_table, cache))
        except Exception as error:
            row["error"] = str(error)
        structure_rows.append(row)
        if index in (6, 7):
            print(json.dumps(row, indent=2), flush=True)
    Path("artifacts/phase_retention_structure.json").write_text(json.dumps(structure_rows, indent=2))

    results = []
    progress = Path("artifacts/phase_retention_progress.jsonl")
    progress.write_text("")
    best_schedules = {}
    for index, (x_table, y_table) in enumerate(terms):
        trials = args.local_trials_term7 if index == 7 else args.local_trials_term6 if index == 6 else 0
        try:
            graph, edges, constant, best, candidates = optimize_term(
                x_table, y_table, cache, local_trials=trials, beam_widths=(64, 256, 1024))
            row = {k: v for k, v in best.items() if k != "actions"}
            old = old_rows[index]
            row.update({"term_index": index, "old_depth": old.get("depth"), "old_cx": old.get("cx"),
                        "old_compute_actions": old.get("compute_actions"),
                        "old_uncompute_actions": old.get("uncompute_actions"),
                        "edge_count": len(edges), "verification": "phase algebra exhaustive"})
            best_schedules[str(index)] = {"actions": best["actions"], "constant": constant}
            for candidate in candidates:
                if "depth" in candidate:
                    progress.open("a").write(json.dumps({"term_index": index, "scheduler": candidate["scheduler"],
                                                          "depth": candidate["depth"], "cx": candidate["cx"],
                                                          "actions": len(candidate["actions"])}) + "\n")
        except Exception as error:
            row = {"term_index": index, "feasible": False, "error": str(error)}
        row["feasible"] = True if "error" not in row else False
        results.append(row)
        print(json.dumps(row), flush=True)
    Path("artifacts/phase_retention_pair_metrics.json").write_text(json.dumps(results, indent=2))
    Path("artifacts/phase_retention_schedules.json").write_text(json.dumps(best_schedules, indent=2))


if __name__ == "__main__":
    main()
