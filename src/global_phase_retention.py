"""Global dirty-ancilla phase-edge retention across all rank terms.

The earlier phase-pebble compiler optimized each rank-factor product
independently and returned the six temporary wires to zero after every edge.
This diagnostic keeps one combined dependency graph and lets phase edges from
different products share live intermediates.  It emits a candidate only after
the exact phase-edge algebra and the final serialized oracle are checked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from qiskit import qasm2, transpile
from qiskit import QuantumCircuit

from phase_pebble_rank import make_pair_graph, phase_edges, verify_phase_edges
from phase_retention import (
    beam_schedule,
    execute_actions,
    greedy_schedule,
    order_seeds,
    score,
)


ROOT = Path(__file__).resolve().parents[1]


class CombinedGraph:
    def __init__(self, nodes: dict[int, tuple[frozenset[int], frozenset[int]]]):
        self.nodes = nodes


SIDE_MASK = (1 << 64) - 1


def _signal_table(signal: int) -> int:
    if signal == -1:
        return SIDE_MASK
    if signal < 6:
        return sum(1 << value for value in range(64) if (value >> signal) & 1)
    if signal < 12:
        bit = signal - 6
        return sum(1 << value for value in range(64) if (value >> bit) & 1)
    raise ValueError(signal)


def _node_table(graph, node: int, memo: dict[int, int]) -> int:
    if node in memo:
        return memo[node]
    left, right = graph.nodes[node]

    def form_table(form):
        result = 0
        for signal in form:
            if signal == -1:
                result ^= SIDE_MASK
            elif signal < 12:
                result ^= _signal_table(signal)
            else:
                result ^= _node_table(graph, signal, memo)
        return result

    memo[node] = form_table(left) & form_table(right)
    return memo[node]


def build_global(cache: dict, terms: list[list[int]]):
    nodes: dict[int, tuple[frozenset[int], frozenset[int]]] = {}
    edges: set[tuple[int, int]] = set()
    constant = False
    per_term = []
    canonical: dict[tuple[str, int], int] = {}
    next_canonical = 20000
    for term_index, (x_table, y_table) in enumerate(terms):
        graph, x_root, y_root, representation = make_pair_graph(
            x_table, y_table, cache
        )
        memo: dict[int, int] = {}
        raw_to_canonical: dict[int, int] = {}
        # Graph construction numbers dependencies before their users.  The
        # recursive table evaluator also handles the fallback graphs safely.
        for node in sorted(graph.nodes):
            if node < 12:
                continue
            table = _node_table(graph, node, memo)
            side = "x" if node < 100 else "y"
            key = (side, table)
            if key not in canonical:
                canonical[key] = next_canonical
                next_canonical += 1
            raw_to_canonical[node] = canonical[key]

        def remap_form(form):
            return frozenset(
                value if value < 12 else raw_to_canonical[value]
                for value in form
            )

        remapped_nodes = {
            raw_to_canonical[node]: (remap_form(left), remap_form(right))
            for node, (left, right) in graph.nodes.items()
            if node >= 12
        }
        # Equivalent truth tables should have identical definitions.  The
        # assertion catches accidental cross-side or hash-key collisions.
        for node, definition in remapped_nodes.items():
            prior = nodes.get(node)
            if prior is not None and prior != definition:
                raise AssertionError("canonical node has inconsistent definition")
            nodes[node] = definition

        def remap_root(root):
            return frozenset(
                value if value < 12 else raw_to_canonical[value]
                for value in root
            )

        rx = remap_root(x_root)
        ry = remap_root(y_root)
        term_edges, term_constant = phase_edges(rx, ry)
        for edge in term_edges:
            # Phase terms add over GF(2), so duplicate edges cancel globally.
            if edge in edges:
                edges.remove(edge)
            else:
                edges.add(edge)
        constant ^= term_constant
        verify_phase_edges(
            CombinedGraph(remapped_nodes), rx, ry, term_edges, term_constant
        )
        per_term.append({
            "term": term_index,
            "representation": representation,
            "x_root_constituents": len(rx),
            "y_root_constituents": len(ry),
            "phase_edges_before_global_cancellation": len(term_edges),
        })
    return CombinedGraph(nodes), sorted(edges), constant, per_term


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--beam-width", type=int, default=256)
    parser.add_argument("--cache", type=Path,
                        default=ROOT / "artifacts" / "minmc_factor_cache.json")
    parser.add_argument("--terms", type=Path,
                        default=ROOT / "artifacts" / "rank_mc_pareto_terms.json")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "artifacts" / "destructive_semantic" /
                        "global_phase_retention.metrics.json")
    args = parser.parse_args()

    cache = json.loads(args.cache.read_text())["functions"]
    terms = json.loads(args.terms.read_text())
    graph, edges, constant, per_term = build_global(cache, terms)

    candidates = []
    for name, order in order_seeds(edges).items():
        try:
            actions = greedy_schedule(graph, edges, order)
            circuit, action_metrics = execute_actions(graph, edges, actions, constant)
            depth, cx = score(circuit)
            candidates.append({"scheduler": "greedy_" + name,
                               "actions": actions, "depth": depth, "cx": cx,
                               **action_metrics})
        except (ValueError, AssertionError) as error:
            candidates.append({"scheduler": "greedy_" + name, "error": str(error)})

    try:
        actions = beam_schedule(graph, edges, args.beam_width)
        circuit, action_metrics = execute_actions(graph, edges, actions, constant)
        depth, cx = score(circuit)
        candidates.append({"scheduler": f"beam_{args.beam_width}",
                           "actions": actions, "depth": depth, "cx": cx,
                           **action_metrics})
    except (ValueError, AssertionError) as error:
        candidates.append({"scheduler": f"beam_{args.beam_width}",
                           "error": str(error)})

    complete = [row for row in candidates if "depth" in row]
    result = {
        "experiment": "global dirty-ancilla phase-edge retention",
        "term_count": len(terms),
        "node_count": len(graph.nodes),
        "global_phase_edge_count": len(edges),
        "constant_phase": constant,
        "per_term": per_term,
        "candidates": [
            {key: value for key, value in row.items() if key != "actions"}
            for row in candidates
        ],
        "status": "complete_schedule_found" if complete else "no_complete_schedule",
    }
    if complete:
        best = min(complete, key=lambda row: (row["depth"], row["cx"],
                                               len(row["actions"])))
        circuit, _ = execute_actions(graph, edges, best["actions"], constant)
        qasm_path = args.out.with_suffix(".qasm")
        qasm_path.write_text(qasm2.dumps(transpile(
            circuit, basis_gates=["u3", "cx"],
            qubits_initially_zero=False, optimization_level=3,
        )))
        result["best"] = {key: value for key, value in best.items()
                           if key != "actions"}
        result["qasm"] = str(qasm_path)
        result["qasm_sha256"] = hashlib.sha256(qasm_path.read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
