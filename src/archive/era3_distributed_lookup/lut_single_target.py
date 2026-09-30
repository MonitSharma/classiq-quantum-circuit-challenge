"""LUT-based reversible-synthesis inventory and early native-cost screen.

ABC supplies conventional k-LUT mappings of the exact 12-input logo function.
This module keeps each LUT intact as a reversible single-target operation
``target ^= h(controls)``.  It records classical topology and compiles the
small local operations directly to ``u3``/``cx`` for a quantum-aware cost
database.  It deliberately does not claim that an irreversible ABC network is
already a reversible schedule.
"""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator

ROOT = Path(__file__).resolve().parents[1]
ABC = ROOT / "experiments/abc/abc"
BENCH = ROOT / "experiments/logo.bench"
POINTS = 1 << 12


@dataclass
class BlifNode:
    name: str
    inputs: tuple[str, ...]
    cubes: tuple[tuple[str, str], ...]

    def truth_table(self) -> int:
        if not self.cubes:
            return 0
        default = 0 if self.cubes[0][1] == "1" else 1
        value = 0
        for assignment in range(1 << len(self.inputs)):
            output = default
            bits = "".join(str((assignment >> i) & 1) for i in range(len(self.inputs)))
            for cube, result in self.cubes:
                if all(c == "-" or c == bit for c, bit in zip(cube, bits)):
                    output = int(result)
                    break
            value |= output << assignment
        return value


def run_abc(k: int, output: Path) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = (
        f"read_bench {BENCH}; strash; balance; rewrite; refactor; resub; "
        f"if -K {k}; write_blif {output}"
    )
    result = subprocess.run([str(ABC), "-c", command], cwd=ROOT, text=True,
                            capture_output=True, check=True)
    return result.stdout + result.stderr


def parse_blif(path: Path) -> tuple[dict[str, BlifNode], tuple[str, ...]]:
    lines = [line.strip() for line in path.read_text().splitlines()]
    nodes: dict[str, BlifNode] = {}
    outputs: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith(".outputs"):
            outputs.extend(line.split()[1:])
        if line.startswith(".names"):
            names = line.split()[1:]
            inputs, output = tuple(names[:-1]), names[-1]
            cubes = []
            index += 1
            while index < len(lines) and lines[index] and not lines[index].startswith("."):
                parts = lines[index].split()
                cubes.append((parts[0], parts[1] if len(parts) > 1 else "1"))
                index += 1
            nodes[output] = BlifNode(output, inputs, tuple(cubes))
            continue
        index += 1
    return nodes, tuple(outputs)


def evaluate_network(nodes: dict[str, BlifNode], output: str, point: int) -> int:
    values = {f"x{i:02d}": (point >> i) & 1 for i in range(12)}
    def evaluate(name: str) -> int:
        if name in values:
            return values[name]
        node = nodes[name]
        local = sum(evaluate(input_name) << i for i, input_name in enumerate(node.inputs))
        values[name] = (node.truth_table() >> local) & 1
        return values[name]
    return evaluate(output)


def exact_network(nodes: dict[str, BlifNode], outputs: tuple[str, ...]) -> bool:
    return all(
        evaluate_network(nodes, outputs[0], point)
        == int(__import__("search").logo(point & 63, point >> 6))
        for point in range(POINTS)
    )


def topological_order(nodes: dict[str, BlifNode], outputs: tuple[str, ...]) -> list[str]:
    ordered: list[str] = []
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name.startswith("x") or name in visited:
            return
        for input_name in nodes[name].inputs:
            visit(input_name)
        visited.add(name)
        ordered.append(name)

    for output in outputs:
        visit(output)
    return ordered


def network_metrics(nodes: dict[str, BlifNode], outputs: tuple[str, ...], k: int,
                    local_depths: dict[str, int] | None = None,
                    local_cx: dict[str, int] | None = None) -> dict:
    order = topological_order(nodes, outputs)
    fanout = Counter(input_name for node in nodes.values() for input_name in node.inputs)
    level: dict[str, int] = {f"x{i:02d}": 0 for i in range(12)}
    for name in order:
        node = nodes[name]
        level[name] = 1 + max((level[input_name] for input_name in node.inputs), default=0)
    last_use = {name: 0 for name in level}
    for position, name in enumerate(order, start=1):
        node = nodes[name]
        for input_name in node.inputs:
            last_use[input_name] = max(last_use[input_name], position)
    end = len(nodes) + 1
    for output in outputs:
        last_use[output] = end
    live = set(f"x{i:02d}" for i in range(12))
    peak = len(live)
    for position, name in enumerate(order, start=1):
        node = nodes[name]
        live.update(node.inputs)
        live.add(name)
        live = {signal for signal in live if last_use[signal] >= position}
        peak = max(peak, len(live))
    weighted: dict[str, int] = {f"x{i:02d}": 0 for i in range(12)}
    weighted_cx: dict[str, int] = {f"x{i:02d}": 0 for i in range(12)}
    if local_depths is not None:
        for name in order:
            weighted[name] = local_depths[name] + max(
                (weighted[input_name] for input_name in nodes[name].inputs), default=0
            )
    if local_cx is not None:
        for name in order:
            weighted_cx[name] = local_cx[name] + max(
                (weighted_cx[input_name] for input_name in nodes[name].inputs), default=0
            )
    weighted_level = lambda name: weighted[name]
    weighted_cx_level = lambda name: weighted_cx[name]
    arities = [len(node.inputs) for node in nodes.values()]
    return {
        "lut_limit": k,
        "lut_count": len(nodes),
        "lut_levels": max(level.values(), default=0),
        "max_lut_arity": max(arities, default=0),
        "arity_histogram": dict(sorted(Counter(arities).items())),
        "max_fanout": max(fanout.values(), default=0),
        "peak_live_signals_topological": peak,
        "exact_4096_inputs": exact_network(nodes, outputs),
        "optimistic_native_critical_depth": (
            max((weighted_level(name) for name in order), default=0)
            if local_depths is not None else None
        ),
        "optimistic_native_critical_cx": (
            max((weighted_cx_level(name) for name in order), default=0)
            if local_cx is not None else None
        ),
    }


def table_bits(value: int, arity: int) -> list[int]:
    return [(value >> i) & 1 for i in range(1 << arity)]


def anf_coefficients(value: int, arity: int) -> list[int]:
    """Return ANF coefficients indexed by monomial mask."""
    coefficients = table_bits(value, arity)
    for bit in range(arity):
        for mask in range(1 << arity):
            if mask & (1 << bit):
                coefficients[mask] ^= coefficients[mask ^ (1 << bit)]
    return coefficients


def canonical_lut(value: int, arity: int) -> tuple[int, tuple[int, ...], int]:
    """Canonicalize under input permutation/negation and output negation."""
    best = None
    for permutation in itertools.permutations(range(arity)):
        for input_mask in range(1 << arity):
            transformed = 0
            for assignment in range(1 << arity):
                source = 0
                for new_bit, old_bit in enumerate(permutation):
                    bit = ((assignment >> new_bit) & 1) ^ ((input_mask >> old_bit) & 1)
                    source |= bit << old_bit
                output = (value >> source) & 1
                transformed |= output << assignment
            for output_negation in (0, 1):
                candidate = transformed ^ (((1 << (1 << arity)) - 1) if output_negation else 0)
                key = (candidate, permutation, input_mask, output_negation)
                if best is None or key < best:
                    best = key
    assert best is not None
    return best[0], best[1], best[2]


def anf_circuit(value: int, arity: int) -> QuantumCircuit:
    circuit = QuantumCircuit(arity + 1)
    coefficients = anf_coefficients(value, arity)
    if coefficients[0]:
        circuit.x(arity)
    for mask in range(1, 1 << arity):
        if not coefficients[mask]:
            continue
        controls = [bit for bit in range(arity) if mask & (1 << bit)]
        if len(controls) == 1:
            circuit.cx(controls[0], arity)
        else:
            circuit.mcx(controls, arity)
    return circuit


def minterm_circuit(value: int, arity: int, complement: bool = False) -> QuantumCircuit:
    circuit = QuantumCircuit(arity + 1)
    selected = [assignment for assignment in range(1 << arity)
                if ((value >> assignment) & 1) == (0 if complement else 1)]
    if complement:
        circuit.x(arity)
    for assignment in selected:
        negative = [bit for bit in range(arity) if not (assignment & (1 << bit))]
        if negative:
            circuit.x(negative)
        if arity == 0:
            circuit.x(arity)
        elif arity == 1:
            circuit.cx(0, arity)
        else:
            circuit.mcx(list(range(arity)), arity)
        if negative:
            circuit.x(negative)
    return circuit


def verify_local_gate(compiled, value: int, arity: int) -> None:
    unitary = Operator(compiled).data
    for input_value in range(1 << arity):
        expected_function = (value >> input_value) & 1
        for target_value in (0, 1):
            initial = input_value | (target_value << arity)
            column = unitary[:, initial]
            output = int(abs(column).argmax())
            expected = input_value | ((target_value ^ expected_function) << arity)
            if output != expected or abs(column[output]) < 1 - 1e-8:
                raise AssertionError(
                    f"local LUT mismatch value={value} arity={arity} input={input_value} target={target_value}"
                )


def local_cost(value: int, arity: int) -> dict:
    candidates = {
        "anf": anf_circuit(value, arity),
        "minterms_1": minterm_circuit(value, arity),
        "minterms_0_with_x": minterm_circuit(value, arity, complement=True),
    }
    compiled_candidates = []
    for method, circuit in candidates.items():
        compiled = transpile(circuit, basis_gates=["u3", "cx"],
                             qubits_initially_zero=False, optimization_level=3)
        verify_local_gate(compiled, value, arity)
        compiled_candidates.append((compiled.depth(), compiled.count_ops().get("cx", 0), method, compiled))
    depth, cx_count, method, compiled = min(compiled_candidates, key=lambda item: (item[0], item[1]))
    return {
        "arity": arity,
        "truth_table": value,
        "method": method,
        "depth": depth,
        "cx_count": int(cx_count),
    }


def inventory(k: int, root: Path) -> dict:
    blif = root / f"logo_k{k}.blif"
    abc_output = run_abc(k, blif)
    nodes, outputs = parse_blif(blif)
    result = {"abc_output": abc_output[-4000:], "metrics": None,
              "nodes": [], "local_costs": {}, "canonical_classes": {}}
    node_depths = {}
    node_cx = {}
    for name, node in nodes.items():
        value = node.truth_table()
        arity = len(node.inputs)
        canonical = canonical_lut(value, arity)
        result["nodes"].append({"name": name, "inputs": list(node.inputs),
                                 "arity": arity, "truth_table": value,
                                 "canonical": canonical[0]})
        key = f"{arity}:{canonical[0]}"
        result["canonical_classes"][key] = result["canonical_classes"].get(key, 0) + 1
        if key not in result["local_costs"]:
            result["local_costs"][key] = local_cost(value, arity)
        node_depths[name] = result["local_costs"][key]["depth"]
        node_cx[name] = result["local_costs"][key]["cx_count"]
    result["metrics"] = network_metrics(nodes, outputs, k, node_depths, node_cx)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, choices=(3, 4, 5), nargs="+", default=[3, 4, 5])
    parser.add_argument("--output", type=Path, default=Path("artifacts/lut_single_target_inventory.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {str(k): inventory(k, args.output.parent / "lut_single_target") for k in args.k}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for k, item in report.items():
        print(k, json.dumps(item["metrics"], sort_keys=True))


if __name__ == "__main__":
    main()
