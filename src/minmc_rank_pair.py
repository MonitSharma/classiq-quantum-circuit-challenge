"""Compile bounded-SAT XAG factors into side-separated reversible pairs.

The scalar XAGs come from :mod:`minmc_xag`; this module supplies the
three-live-value reversible pebbling and scores exact standalone pairs.
"""

import json
import heapq
from functools import lru_cache
from pathlib import Path

from qiskit import QuantumCircuit, transpile

from parallel_rank_pair_xag import exact_clear_plan, apply_form
from xag import linear


def mapped_xag(spec, side_offset):
    """Return (node map, output form) using the repository XAG wire IDs."""
    nodes = {}
    for k, node in enumerate(spec["and_nodes"]):
        node_id = 12 + k
        def convert(values):
            result = set()
            for value in values:
                if value == 0:
                    result.add(-1)
                elif 1 <= value <= 6:
                    result.add(side_offset + value - 1)
                else:
                    result.add(12 + value - 7)
            return frozenset(result)
        nodes[node_id] = (convert(node["left"]), convert(node["right"]))
    output = set()
    for value in spec["output"]:
        if value == 0:
            output.add(-1)
        elif 1 <= value <= 6:
            output.add(side_offset + value - 1)
        else:
            output.add(12 + value - 7)
    return nodes, frozenset(output)


class XAG:
    def __init__(self, nodes):
        self.nodes = nodes

    def ancestors(self, forms):
        out = {v for form in forms for v in form if v >= 12}
        stack = list(out)
        while stack:
            node = stack.pop()
            for form in self.nodes[node]:
                for value in form:
                    if value >= 12 and value not in out:
                        out.add(value)
                        stack.append(value)
        return out


def compile_side(spec, inputs, output, scratch):
    nodes, root = mapped_xag(spec, inputs[0])
    graph = XAG(nodes)
    required = {v for v in root if v >= 12}
    circuit = QuantumCircuit(18)
    wire = {inputs[i]: inputs[i] for i in range(6)}
    if not required:
        apply_form(circuit, root, wire, output)
        return circuit
    path = exact_clear_plan(graph, set(), required, limit=3)
    primary = max(required)
    slots = [output, *scratch]

    @lru_cache(None)
    def assign(index, mapping_tuple):
        mapping = dict(mapping_tuple)
        if index == len(path):
            return () if mapping.get(primary) == 0 else None
        node = path[index]
        if node in mapping:
            slot = mapping.pop(node)
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
    for node in path:
        a, b = graph.nodes[node]
        pre, p, r = linear(circuit, a, b, wire)
        planned_node, planned_slot = slot_plan[plan_index]
        plan_index += 1
        if planned_node != node:
            raise AssertionError("XAG slot plan/path mismatch")
        if node in mapping:
            target = slots[mapping.pop(node)]
            wire.pop(node)
        else:
            if planned_slot is None:
                raise AssertionError("invalid live-free uncompute")
            target = slots[planned_slot]
            mapping[node] = planned_slot
            wire[node] = target
        circuit.compose(pre, inplace=True)
        if len({p, r, target}) != 3:
            raise ValueError("overlapping XAG wires")
        circuit.rccx(p, r, target)
        circuit.compose(pre.inverse(), inplace=True)
    if set(mapping) != required:
        raise AssertionError("XAG schedule did not reach roots")
    apply_form(circuit, root, wire, output)
    return circuit


def score(circuit):
    out = transpile(circuit, basis_gates=["u3", "cx"],
                    qubits_initially_zero=False, optimization_level=3)
    return out.depth(), out.count_ops().get("cx", 0)


def main():
    cache = json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    bases = {name: json.loads(Path(f"artifacts/{name}.json").read_text())
             for name in ("pair_terms", "rank_terms", "rank_mc_pareto_terms")}
    results = {}
    for name, terms in bases.items():
        rows = []
        for index, (x, y) in enumerate(terms):
            sx, sy = cache.get(str(x)), cache.get(str(y))
            row = {"term_index": index, "x_solved": sx is not None,
                   "y_solved": sy is not None}
            try:
                if sx is None or sy is None:
                    raise ValueError("factor missing from bounded XAG cache")
                cx = compile_side(sx, list(range(0, 6)), 12, [13, 14])
                cy = compile_side(sy, list(range(6, 12)), 15, [16, 17])
                pre = QuantumCircuit(18)
                pre.compose(cx, inplace=True)
                pre.compose(cy, inplace=True)
                pair = pre.copy()
                pair.cz(12, 15)
                pair.compose(pre.inverse(), inplace=True)
                dx, cxx = score(cx); dy, cxy = score(cy)
                dp, cxp = score(pre); d, c = score(pair)
                row.update({"x_depth": dx, "x_cx": cxx, "y_depth": dy,
                            "y_cx": cxy, "parallel_compute_depth": dp,
                            "parallel_compute_cx": cxp, "pair_depth": d,
                            "pair_cx": c, "width": 18})
            except (ValueError, IndexError) as error:
                row["error"] = str(error)
            rows.append(row)
            print(name, index, row, flush=True)
        results[name] = rows
    Path("artifacts/minmc_rank_pair_metrics.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
