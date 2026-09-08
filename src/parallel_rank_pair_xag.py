"""Side-separated rank-pair compiler with a three-ancilla XAG pebble budget."""

import json
import heapq
from functools import lru_cache
from pathlib import Path

from qiskit import QuantumCircuit, transpile

from formula import formula, remap
from xag import Graph, linear, plan


def exact_clear_plan(graph, start, keep, limit=3, max_states=300000):
    """Find a legal toggle path whose final live set is exactly ``keep``."""
    scope = graph.ancestors([start]) | graph.ancestors([keep]) | set(start) | set(keep)
    ids = sorted(scope)
    pos = {node: i for i, node in enumerate(ids)}
    dependencies = {
        node: sum(1 << pos[parent] for parent in set().union(*graph.nodes[node])
                  if parent >= 12)
        for node in ids
    }
    start_mask = sum(1 << pos[node] for node in start)
    goal_mask = sum(1 << pos[node] for node in keep)
    distances = {start_mask: 0}
    parents = {}
    queue = [(0, start_mask)]
    while queue:
        distance, state = heapq.heappop(queue)
        if distance != distances.get(state):
            continue
        if state == goal_mask:
            path = []
            while state != start_mask:
                previous, node = parents[state]
                path.append(node)
                state = previous
            return path[::-1]
        if len(distances) > max_states:
            raise ValueError("exact cleanup search size")
        if state.bit_count() > limit:
            continue
        for node in ids:
            bit = 1 << pos[node]
            if state & bit:
                if state & dependencies[node] != dependencies[node]:
                    continue
                next_state = state ^ bit
            else:
                if state & dependencies[node] != dependencies[node] or state.bit_count() >= limit:
                    continue
                next_state = state ^ bit
            if next_state not in distances:
                distances[next_state] = distance + 1
                parents[next_state] = (state, node)
                heapq.heappush(queue, (distance + 1, next_state))
    raise ValueError("exact cleanup not pebbleable")


def apply_form(q, form, wire, target):
    for value in form:
        if value == -1:
            q.x(target)
        else:
            if wire[value] != target:
                q.cx(wire[value], target)


def compile_side(table, inputs, output, scratch):
    graph = Graph()
    expression = remap(formula(table, 6), range(6))
    root = graph.expr(expression)
    wire = {i: inputs[i] for i in range(6)}
    circuit = QuantumCircuit(18)

    nodes = set(v for v in root if v >= 12)
    if not nodes:
        apply_form(circuit, root, wire, output)
        return circuit
    try:
        path = exact_clear_plan(graph, set(), nodes, limit=3)
    except ValueError as error:
        raise ValueError(f"three-ancilla schedule unavailable: {error}") from error

    primary = max(nodes)
    slots = [output, *scratch]

    @lru_cache(None)
    def assign(index, mapping_tuple):
        mapping = dict(mapping_tuple)
        if index == len(path):
            return () if primary in mapping and mapping[primary] == 0 else None
        node = path[index]
        if node in mapping:
            slot = mapping[node]
            mapping.pop(node)
            suffix = assign(index + 1, tuple(sorted(mapping.items())))
            return None if suffix is None else ((node, None), *suffix)
        occupied = set(mapping.values())
        candidates = [slot for slot in range(3) if slot not in occupied]
        if node == primary:
            candidates = [slot for slot in candidates if slot == 0]
        for slot in candidates:
            mapping[node] = slot
            suffix = assign(index + 1, tuple(sorted(mapping.items())))
            if suffix is not None:
                return ((node, slot), *suffix)
            mapping.pop(node)
        return None

    slot_plan = assign(0, ())
    if slot_plan is None:
        raise ValueError("three-slot schedule cannot pin output node")

    mapping = {}
    plan_index = 0

    def toggle(node):
        nonlocal plan_index
        a, b = graph.nodes[node]
        pre, p, r = linear(circuit, a, b, wire)
        planned_node, planned_slot = slot_plan[plan_index]
        plan_index += 1
        if planned_node != node:
            raise AssertionError("XAG slot plan/path mismatch")
        if node in mapping:
            target = slots[mapping.pop(node)]
            wire.pop(node, None)
        else:
            if planned_slot is None:
                raise AssertionError("uncompute plan for live-free XAG node")
            target = slots[planned_slot]
            mapping[node] = planned_slot
            wire[node] = target
        circuit.compose(pre, inplace=True)
        if len({p, r, target}) != 3:
            raise ValueError(f"overlapping XAG wires node={node} p={p} r={r} target={target}")
        circuit.rccx(p, r, target)
        circuit.compose(pre.inverse(), inplace=True)
        if node in mapping:
            # The node was just computed; the mapping is already recorded.
            pass

    for node in path:
        toggle(node)
    apply_form(circuit, root, wire, output)

    if set(mapping) != nodes:
        raise AssertionError(f"XAG schedule did not reach exact root set: live={mapping} roots={nodes}")
    return circuit


def parallel_pair(a, b):
    x = compile_side(a, list(range(0, 6)), 12, [13, 14])
    y = compile_side(b, list(range(6, 12)), 15, [16, 17])
    pre = QuantumCircuit(18)
    pre.compose(x, inplace=True)
    pre.compose(y, inplace=True)
    pair = pre.copy()
    pair.cz(12, 15)
    pair.compose(pre.inverse(), inplace=True)
    return x, y, pre, pair


def score_pair(a, b):
    x, y, pre, pair = parallel_pair(a, b)
    def score(circuit):
        compiled = transpile(circuit, basis_gates=["u3", "cx"],
                             qubits_initially_zero=False, optimization_level=3)
        return compiled.depth(), compiled.count_ops().get("cx", 0)
    x_score = score(x)
    y_score = score(y)
    pre_score = score(pre)
    pair_score = score(pair)
    return {
        "x_depth": x_score[0], "x_cx": x_score[1],
        "y_depth": y_score[0], "y_cx": y_score[1],
        "parallel_compute_depth": pre_score[0], "parallel_compute_cx": pre_score[1],
        "pair_depth": pair_score[0], "pair_cx": pair_score[1], "width": 18,
    }


def main():
    bases = {
        "pair_terms": json.loads(Path("artifacts/pair_terms.json").read_text()),
        "rank_terms": json.loads(Path("artifacts/rank_terms.json").read_text()),
        "rank_mc_pareto_terms": json.loads(Path("artifacts/rank_mc_pareto_terms.json").read_text()),
    }
    results = {}
    for name, terms in bases.items():
        rows = []
        for index, (a, b) in enumerate(terms):
            try:
                row = {"term_index": index, **score_pair(a, b)}
            except (ValueError, IndexError) as error:
                row = {"term_index": index, "error": str(error)}
            rows.append(row)
            print(name, index, row, flush=True)
        results[name] = rows
    Path("artifacts/parallel_rank_pair_xag_metrics.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
