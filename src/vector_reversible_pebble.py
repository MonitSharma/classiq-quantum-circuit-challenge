"""Parse an ABC two-input LUT network into an affine-plus-AND graph.

The parser is the bridge from the irreversible inventory to reversible
pebbling.  Every two-input Boolean LUT has an ANF consisting of a constant,
two linear terms, and at most one product term.  We keep the product as a
graph node and represent the rest as an affine form over six inputs and prior
product nodes.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from xag import linear, plan
from vector_feature_analysis import ARTIFACTS, FEATURES, truth_rows

FULL = (1 << 64) - 1
INPUT_TT = [sum(1 << y for y in range(64) if y & (1 << bit)) for bit in range(6)]
INPUT_RE = re.compile(r"^INPUT\(([^)]+)\)")
ASSIGN_RE = re.compile(r"^(\w+)\s*=\s*LUT\s+0x([0-9a-fA-F]+)\s*\(\s*([^)]*)\)")
OUTPUT_RE = re.compile(r"^OUTPUT\(([^)]+)\)")


@dataclass
class AffineAndGraph:
    inputs: int
    nodes: dict[int, tuple[frozenset[int], frozenset[int]]]
    outputs: dict[str, frozenset[int]]
    signal_names: dict[str, int]
    truth: dict[int, int]


def xor_form(left: frozenset[int], right: frozenset[int]) -> frozenset[int]:
    return left ^ right


def form_value(form: frozenset[int], truth: dict[int, int]) -> int:
    result = 0
    for signal in form:
        result ^= FULL if signal == -1 else truth[signal]
    return result


def parse(path: Path) -> AffineAndGraph:
    names: dict[str, int] = {}
    truth: dict[int, int] = {}
    forms: dict[int, frozenset[int]] = {}
    nodes: dict[int, tuple[frozenset[int], frozenset[int]]] = {}
    output_names: list[str] = []
    next_signal = 0
    for raw in path.read_text().splitlines():
        line = raw.strip()
        match = INPUT_RE.match(line)
        if match:
            name = match.group(1)
            names[name] = next_signal
            truth[next_signal] = INPUT_TT[next_signal]
            forms[next_signal] = frozenset([next_signal])
            next_signal += 1
            continue
        match = ASSIGN_RE.match(line)
        if match:
            name, code_text, args_text = match.groups()
            args = [item.strip() for item in args_text.split(",") if item.strip()]
            if len(args) not in (1, 2):
                raise ValueError(f"unsupported LUT arity in {line!r}")
            left_name = args[0]
            left = names[left_name]
            right = names[args[1]] if len(args) == 2 else None
            code = int(code_text, 16) & 0xF
            c0 = (code >> 0) & 1
            ca = ((code >> 1) & 1) ^ c0
            cb = (((code >> 2) & 1) ^ c0) if right is not None else 0
            cab = (((code >> 3) & 1) ^ ((code >> 2) & 1) ^ ((code >> 1) & 1) ^ c0) if right is not None else 0
            value = (FULL if c0 else 0) ^ (truth[left] if ca else 0) ^ (truth[right] if cb else 0)
            affine = forms[left] if ca else frozenset()
            affine = xor_form(affine, forms[right]) if cb else affine
            if c0:
                affine = xor_form(affine, frozenset([-1]))
            if cab and left != right:
                node = next_signal
                next_signal += 1
                nodes[node] = (forms[left], forms[right])
                truth[node] = form_value(forms[left], truth) & form_value(forms[right], truth)
                affine = xor_form(affine, frozenset([node]))
            elif cab:
                affine = xor_form(affine, forms[left])
            value = form_value(affine, truth)
            names[name] = next_signal
            forms[next_signal] = affine
            truth[next_signal] = value
            next_signal += 1
            continue
        match = OUTPUT_RE.match(line)
        if match:
            output_names.append(match.group(1))
    outputs = {name: forms[names[name]] for name in output_names}
    graph = AffineAndGraph(6, nodes, outputs, names, truth)
    return graph


def verify(graph: AffineAndGraph) -> dict:
    rows = truth_rows()
    expected = {name: sum(row[name] << row["y"] for row in rows) for name in FEATURES}
    actual = {name: form_value(form, graph.truth) for name, form in graph.outputs.items()}
    mismatches = {
        name: {"expected": expected[name], "actual": actual.get(name)}
        for name in FEATURES if actual.get(name) != expected[name]
    }
    return {
        "outputs": list(graph.outputs),
        "product_nodes": len(graph.nodes),
        "mismatches": mismatches,
        "exact": not mismatches,
        "output_form_sizes": {name: len(form) for name, form in graph.outputs.items()},
    }


class PlanGraph:
    """Adapter for the repository's bounded reversible pebble planner."""

    def __init__(self, graph: AffineAndGraph):
        self.nodes = graph.nodes

    def ancestors(self, forms):
        result = {signal for form in forms for signal in form if signal >= 6}
        stack = list(result)
        while stack:
            signal = stack.pop()
            for form in self.nodes[signal]:
                for dependency in form:
                    if dependency >= 6 and dependency not in result:
                        result.add(dependency)
                        stack.append(dependency)
        return result


def compile_single_output(graph: AffineAndGraph, name: str) -> QuantumCircuit:
    """Compile one output using five graph pebbles and one clean target wire."""
    target = 12
    free = [13, 14, 15, 16, 17]
    wire = {index: 6 + index for index in range(6)}
    live: set[int] = set()
    circuit = QuantumCircuit(18)
    planner = PlanGraph(graph)
    path = plan(planner, frozenset(), [graph.outputs[name]], limit=5,
                max_states=500_000)

    def toggle(signal: int) -> None:
        left, right = graph.nodes[signal]
        pre, pivot, other = linear(circuit, left, right, wire)
        if signal in live:
            physical = wire[signal]
        else:
            if not free:
                raise AssertionError("planner exceeded the physical pebble budget")
            physical = free.pop(0)
            wire[signal] = physical
        circuit.compose(pre, inplace=True)
        circuit.rccx(pivot, other, physical)
        circuit.compose(pre.inverse(), inplace=True)
        if signal in live:
            live.remove(signal)
            free.append(wire.pop(signal))
            free.sort()
        else:
            live.add(signal)

    for signal in path:
        toggle(signal)
    form = graph.outputs[name]
    if -1 in form:
        circuit.x(target)
    for signal in form:
        if signal != -1:
            circuit.cx(wire[signal], target)
    for signal in reversed(path):
        toggle(signal)
    if live:
        raise AssertionError("single-output pebble schedule did not clear")
    return circuit


def main() -> None:
    path = ARTIFACTS / "vector_feature_abc_strash_balance_rewrite_refactor_resub.bench"
    graph = parse(path)
    report = verify(graph)
    report["source"] = str(path.relative_to(path.parents[1]))
    report["product_node_ids"] = sorted(graph.nodes)
    (ARTIFACTS / "vector_feature_reversible_graph.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    try:
        raw = compile_single_output(graph, "A")
        compiled = transpile(raw, basis_gates=["u3", "cx"],
                             qubits_initially_zero=False,
                             optimization_level=3)
        path = ARTIFACTS / "vector_loader_A_pebbled.qasm"
        path.write_text(qasm2.dumps(compiled))
        report["A_pebbled"] = {
            "depth": compiled.depth(),
            "cx": compiled.count_ops().get("cx", 0),
            "width": compiled.num_qubits,
            "path": str(path.relative_to(ROOT)),
        }
    except ValueError as error:
        report["A_pebbled"] = {"error": str(error)}
    (ARTIFACTS / "vector_feature_reversible_graph.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
