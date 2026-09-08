"""Phase-aware reversible compiler for rank-factor pairs.

Unlike the side-separated compiler, this module never materializes a complete
rank-factor output.  It expands each product of root XOR constituents into
phase edges, computes only the ancestors needed for one edge, applies the
diagonal phase, and reverses the pebble path.  All six clean ancillas are one
shared pool.

This is deliberately a measured research compiler: every candidate is built
as a QuantumCircuit and transpiled with ``qubits_initially_zero=False``.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile

from formula import formula, remap
from xag import Graph, linear, plan


ANCILLAS = tuple(range(12, 18))


class CombinedGraph:
    """Minimal graph interface consumed by the existing pebble planner."""

    def __init__(self, x_graph: Graph, y_graph: Graph):
        self.nodes = dict(x_graph.nodes)
        self.nodes.update(y_graph.nodes)

    def ancestors(self, forms):
        out = {value for form in forms for value in form if value >= 12}
        stack = list(out)
        while stack:
            node = stack.pop()
            for form in self.nodes[node]:
                for value in form:
                    if value >= 12 and value not in out:
                        out.add(value)
                        stack.append(value)
        return out


def _root_graph(table: int, side: str) -> tuple[CombinedGraph, frozenset[int]]:
    graph = Graph()
    if side == "x":
        expression = remap(formula(table, 6), range(6))
        return graph, graph.expr(expression)
    expression = remap(formula(table, 6), range(6, 12))
    # Offset y nonlinear node IDs so x and y nodes can share one pool.
    y_root = graph.expr(expression)
    nodes = {}
    remap_nodes = {}
    next_id = 100
    for node in sorted(graph.nodes):
        if node < 12:
            continue
        remap_nodes[node] = next_id
        next_id += 1
    for node, (left, right) in graph.nodes.items():
        if node < 12:
            continue
        translate = lambda form: frozenset(
            remap_nodes.get(value, value) for value in form
        )
        nodes[remap_nodes[node]] = (translate(left), translate(right))
    result = CombinedGraph(Graph(), Graph())
    result.nodes = nodes
    return result, frozenset(remap_nodes.get(value, value) for value in y_root)


def _cached_graph(table: int, side: str, cache: dict) -> tuple[dict, frozenset[int]] | None:
    spec = cache.get(str(table))
    if spec is None:
        return None
    offset = 0 if side == "x" else 6
    node_ids = {index: (12 + index if side == "x" else 100 + index)
                for index in range(len(spec["and_nodes"]))}

    def form(values):
        result = set()
        for value in values:
            if value == 0:
                result.add(-1)
            elif 1 <= value <= 6:
                result.add(offset + value - 1)
            else:
                result.add(node_ids[value - 7])
        return frozenset(result)

    nodes = {
        node_ids[index]: (form(node["left"]), form(node["right"]))
        for index, node in enumerate(spec["and_nodes"])
    }
    root = form(spec["output"])
    return nodes, root


def make_pair_graph(x_table: int, y_table: int, cache: dict) -> tuple[CombinedGraph, frozenset[int], frozenset[int], str]:
    x_cached = _cached_graph(x_table, "x", cache)
    y_cached = _cached_graph(y_table, "y", cache)
    if x_cached is not None and y_cached is not None:
        x_nodes, x_root = x_cached
        y_nodes, y_root = y_cached
        graph = CombinedGraph(Graph(), Graph())
        graph.nodes = {**x_nodes, **y_nodes}
        return graph, x_root, y_root, "bounded_low_and_xag"

    # Fallback keeps the module useful for factors absent from the bounded
    # cache, but those rows are labelled formula_fallback in the report.
    x_graph = Graph()
    x_root = x_graph.expr(remap(formula(x_table, 6), range(6)))
    y_graph = Graph()
    y_root_raw = y_graph.expr(remap(formula(y_table, 6), range(6, 12)))
    y_map = {node: 100 + index for index, node in enumerate(sorted(y_graph.nodes)) if node >= 12}
    nodes = dict(x_graph.nodes)
    for node, (left, right) in y_graph.nodes.items():
        if node < 12:
            continue
        translate = lambda form: frozenset(y_map.get(value, value) for value in form)
        nodes[y_map[node]] = (translate(left), translate(right))
    graph = CombinedGraph(Graph(), Graph())
    graph.nodes = nodes
    y_root = frozenset(y_map.get(value, value) for value in y_root_raw)
    return graph, x_root, y_root, "formula_fallback"


def phase_edges(x_root: frozenset[int], y_root: frozenset[int]) -> tuple[set[tuple[int, int]], bool]:
    """Return GF(2)-cancelled constituent products and constant-phase flag."""
    edges: set[tuple[int, int]] = set()
    constant = False
    for x_value in x_root:
        for y_value in y_root:
            if x_value == -1 and y_value == -1:
                constant = not constant
            elif x_value == -1:
                edge = (-1, y_value)
                edges.symmetric_difference_update((edge,))
            elif y_value == -1:
                edge = (x_value, -1)
                edges.symmetric_difference_update((edge,))
            else:
                edge = (x_value, y_value)
                edges.symmetric_difference_update((edge,))
    return edges, constant


def _eval_form(graph: CombinedGraph, form: frozenset[int], assignment: dict[int, int], memo: dict[int, int]) -> int:
    value = 0
    for signal in form:
        if signal == -1:
            value ^= 1
        elif signal in assignment:
            value ^= assignment[signal]
        else:
            if signal not in memo:
                left, right = graph.nodes[signal]
                memo[signal] = _eval_form(graph, left, assignment, memo) & _eval_form(graph, right, assignment, memo)
            value ^= memo[signal]
    return value


def verify_phase_edges(graph: CombinedGraph, x_root: frozenset[int], y_root: frozenset[int],
                       edges: set[tuple[int, int]], constant: bool) -> None:
    """Check the GF(2) edge expansion on all 4096 classical inputs."""
    for x in range(64):
        for y in range(64):
            assignment = {bit: (x >> bit) & 1 for bit in range(6)}
            assignment.update({6 + bit: (y >> bit) & 1 for bit in range(6)})
            memo: dict[int, int] = {}
            expected = _eval_form(graph, x_root, assignment, memo) & _eval_form(graph, y_root, assignment, memo)
            actual = int(constant)
            for left, right in edges:
                lvalue = 1 if left == -1 else _eval_form(graph, frozenset((left,)), assignment, memo)
                rvalue = 1 if right == -1 else _eval_form(graph, frozenset((right,)), assignment, memo)
                actual ^= lvalue & rvalue
            if actual != expected:
                raise AssertionError(f"phase-edge algebra mismatch at x={x}, y={y}")


def _toggle(q: QuantumCircuit, graph: CombinedGraph, node: int, live: set[int], wire: dict[int, int]) -> None:
    left, right = graph.nodes[node]
    pre, pivot, other = linear(q, left, right, wire)
    if node in live:
        target = wire.pop(node)
    else:
        free = sorted(set(ANCILLAS) - set(wire.values()))
        if not free:
            raise ValueError("shared six-ancilla pool exhausted")
        target = free.pop(0)
        wire[node] = target
    q.compose(pre, inplace=True)
    if len({pivot, other, target}) != 3:
        raise ValueError(f"overlapping XAG wires for node {node}")
    q.rccx(pivot, other, target)
    q.compose(pre.inverse(), inplace=True)
    if node in live:
        live.remove(node)
    else:
        live.add(node)


def _phase_edge(q: QuantumCircuit, edge: tuple[int, int], wire: dict[int, int]) -> None:
    left, right = ({edge[0]}, {edge[1]})
    if edge[0] == -1 and edge[1] == -1:
        q.global_phase += np.pi
        return
    if edge[0] == -1:
        q.z(wire[edge[1]])
        return
    if edge[1] == -1:
        q.z(wire[edge[0]])
        return
    pre, pivot, other = linear(q, left, right, wire)
    q.compose(pre, inplace=True)
    q.cz(pivot, other)
    q.compose(pre.inverse(), inplace=True)


def compile_pair(x_table: int, y_table: int, cache: dict, *, max_states: int = 300_000) -> tuple[QuantumCircuit, dict]:
    graph, x_root, y_root, representation = make_pair_graph(x_table, y_table, cache)
    edges, constant = phase_edges(x_root, y_root)
    verify_phase_edges(graph, x_root, y_root, edges, constant)
    q = QuantumCircuit(18)
    live: set[int] = set()
    wire = {index: index for index in range(12)}
    metrics = {
        "x_root_constituents": len(x_root),
        "y_root_constituents": len(y_root),
        "phase_edge_count": len(edges),
        "global_phase": constant,
        "max_live_ancillas": 0,
        "compute_actions": 0,
        "uncompute_actions": 0,
        "phase_actions": len(edges),
        "representation": representation,
    }
    # Deterministic ordering gives reproducible measurements.  A later stage
    # can search edge orderings without changing the circuit semantics.
    for edge in sorted(edges):
        targets = []
        if edge[0] >= 12:
            targets.append(frozenset((edge[0],)))
        if edge[1] >= 12:
            targets.append(frozenset((edge[1],)))
        path = plan(graph, frozenset(live), targets, limit=6, max_states=max_states)
        for node in path:
            was_live = node in live
            _toggle(q, graph, node, live, wire)
            metrics["uncompute_actions" if was_live else "compute_actions"] += 1
            metrics["max_live_ancillas"] = max(metrics["max_live_ancillas"], len(live))
        _phase_edge(q, edge, wire)
        for node in reversed(path):
            was_live = node in live
            _toggle(q, graph, node, live, wire)
            metrics["uncompute_actions" if was_live else "compute_actions"] += 1
            metrics["max_live_ancillas"] = max(metrics["max_live_ancillas"], len(live))
        if live:
            raise AssertionError("edge schedule failed to return to empty pool")
    if constant:
        q.global_phase += np.pi
    return q, metrics


def score(q: QuantumCircuit) -> tuple[int, int]:
    out = transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    return out.depth(), out.count_ops().get("cx", 0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--basis", default="all")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    cache = json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    basis_names = ("pair_terms", "rank_terms", "rank_mc_pareto_terms") if args.basis == "all" else (args.basis,)
    results = {}
    progress = Path("artifacts/phase_pebble_progress.jsonl")
    progress.write_text("")
    for basis in basis_names:
        terms = json.loads(Path(f"artifacts/{basis}.json").read_text())
        rows = []
        for index, (x_table, y_table) in enumerate(terms[: args.limit]):
            row = {"term_index": index, "x_table": x_table, "y_table": y_table}
            try:
                circuit, metrics = compile_pair(x_table, y_table, cache)
                depth, cx = score(circuit)
                row.update(metrics, depth=depth, cx=cx, width=18, feasible=True)
            except (ValueError, IndexError) as error:
                row.update(feasible=False, error=str(error))
            row["basis"] = basis
            rows.append(row)
            progress.open("a").write(json.dumps(row) + "\n")
            print(json.dumps(row), flush=True)
        results[basis] = rows
    Path("artifacts/phase_pebble_pair_metrics.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
