"""Conditionally-clean cofactor experiments.

The first version deliberately keeps the classical analysis separate from the
quantum compiler.  It is intended to make the selector trade-off reproducible
before any complete-oracle integration is attempted.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile

from search import logo
from search import esop


X_BITS = tuple(range(6))
Y_BITS = tuple(range(6, 12))


def bit(value: int, wire: int) -> int:
    return (value >> wire) & 1


def selector_value(x: int, y: int, selector_bits: tuple[tuple[str, int], ...]) -> int:
    value = 0
    for i, (kind, wire) in enumerate(selector_bits):
        source = x if kind == "x" else y
        value |= bit(source, wire) << i
    return value


def residual_coordinates(selector_bits: tuple[tuple[str, int], ...]):
    selected = {(kind, wire) for kind, wire in selector_bits}
    coordinates = [("x", wire) for wire in X_BITS if ("x", wire) not in selected]
    coordinates += [("y", wire) for wire in X_BITS if ("y", wire) not in selected]
    return tuple(coordinates)


def residual_index(x: int, y: int, coordinates) -> int:
    value = 0
    for i, (kind, wire) in enumerate(coordinates):
        source = x if kind == "x" else y
        value |= bit(source, wire) << i
    return value


def cofactor_table(selector_bits, selector_assignment: int, coordinates):
    table = np.zeros(1 << len(coordinates), dtype=np.uint8)
    for x in range(64):
        for y in range(64):
            if selector_value(x, y, selector_bits) != selector_assignment:
                continue
            table[residual_index(x, y, coordinates)] = logo(x, y)
    return table


def gf2_rank(matrix: np.ndarray) -> int:
    matrix = matrix.copy().astype(np.uint8)
    rows, cols = matrix.shape
    rank = 0
    for col in range(cols):
        pivot = next((row for row in range(rank, rows) if matrix[row, col]), None)
        if pivot is None:
            continue
        matrix[[rank, pivot]] = matrix[[pivot, rank]]
        for row in range(rows):
            if row != rank and matrix[row, col]:
                matrix[row] ^= matrix[rank]
        rank += 1
    return rank


def xy_rank(table: np.ndarray, coordinates) -> int:
    x_positions = [i for i, (kind, _) in enumerate(coordinates) if kind == "x"]
    y_positions = [i for i, (kind, _) in enumerate(coordinates) if kind == "y"]
    matrix = np.zeros((1 << len(x_positions), 1 << len(y_positions)), dtype=np.uint8)
    for index, value in enumerate(table):
        if value:
            x = sum(((index >> position) & 1) << i for i, position in enumerate(x_positions))
            y = sum(((index >> position) & 1) << i for i, position in enumerate(y_positions))
            matrix[x, y] = 1
    return gf2_rank(matrix)


def anf_stats(table: np.ndarray):
    coefficients = table.copy().astype(np.uint8)
    n = int(np.log2(len(coefficients)))
    for axis in range(n):
        for mask in range(len(coefficients)):
            if mask & (1 << axis):
                coefficients[mask] ^= coefficients[mask ^ (1 << axis)]
    supports = np.flatnonzero(coefficients)
    return {
        "anf_terms": int(len(supports)),
        "anf_degree": int(max((int(mask).bit_count() for mask in supports), default=0)),
    }


def analyze_selector(selector_bits):
    coordinates = residual_coordinates(selector_bits)
    branches = []
    for assignment in range(1 << len(selector_bits)):
        table = cofactor_table(selector_bits, assignment, coordinates)
        if not np.any(table):
            continue
        branches.append({
            "assignment": assignment,
            "selector_bits": list(selector_bits),
            "coordinates": list(coordinates),
            "residual_variables": len(coordinates),
            "ones": int(table.sum()),
            "xy_rank": xy_rank(table, coordinates),
            **anf_stats(table),
            "truth_table_hex": "0x" + "".join(
                f"{int(v):x}" for v in table[::-1]
            ),
        })
    return {
        "selector_bits": list(selector_bits),
        "selector_size": len(selector_bits),
        "residual_variables": len(coordinates),
        "nonzero_branches": len(branches),
        "branches": branches,
    }


def esop_for_table(table):
    table_int = sum(int(v) << i for i, v in enumerate(table))
    return esop(table_int, int(np.log2(len(table))))


def representation_profile(table):
    cubes = esop_for_table(table)
    supports = [mask.bit_count() for mask, _ in cubes]
    support_counter = Counter(mask for mask, _ in cubes)
    repeated_literals = sum(max(0, count - 1) for count in support_counter.values())
    containment_pairs = 0
    for left, _ in cubes:
        for right, _ in cubes:
            if left != right and left & right == left:
                containment_pairs += 1
    common_pairs = Counter()
    for mask, _ in cubes:
        literals = [i for i in range(mask.bit_length()) if mask >> i & 1]
        for pair in itertools.combinations(literals, 2):
            common_pairs[pair] += 1
    return {
        "esop_cubes": len(cubes),
        "esop_literals": int(sum(supports)),
        "control_histogram": dict(sorted(Counter(supports).items())),
        "max_control": max(supports, default=0),
        "repeated_literal_cubes": repeated_literals,
        "containment_pairs": containment_pairs // 2,
        "common_literal_pairs": int(sum(count - 1 for count in common_pairs.values() if count > 1)),
        "max_common_pair_frequency": max(common_pairs.values(), default=0),
        "ones": int(table.sum()),
        **anf_stats(table),
    }


def selector_signature(selector_bits):
    coordinates = residual_coordinates(selector_bits)
    branches = []
    for assignment in range(1 << len(selector_bits)):
        table = cofactor_table(selector_bits, assignment, coordinates)
        if not np.any(table):
            continue
        profile = representation_profile(table)
        profile["assignment"] = assignment
        branches.append(profile)
    totals = {
        "selector_bits": list(selector_bits),
        "selector_size": len(selector_bits),
        "nonzero_branches": len(branches),
        "residual_variables": len(coordinates),
        "sum_esop_cubes": sum(b["esop_cubes"] for b in branches),
        "sum_esop_literals": sum(b["esop_literals"] for b in branches),
        "sum_containment_pairs": sum(b["containment_pairs"] for b in branches),
        "sum_common_literal_pairs": sum(b["common_literal_pairs"] for b in branches),
        "max_branch_cubes": max((b["esop_cubes"] for b in branches), default=0),
        "max_branch_controls": max((b["max_control"] for b in branches), default=0),
        "branches": branches,
    }
    # Lower is better for the first terms; the last terms reward factorable
    # repeated structure without pretending this is a native-depth score.
    totals["classical_factor_score"] = (
        totals["sum_esop_literals"]
        - 4 * totals["sum_containment_pairs"]
        - 2 * totals["sum_common_literal_pairs"]
    )
    return totals


def all_selector_sets(size):
    wires = tuple(("x", i) for i in range(6)) + tuple(("y", i) for i in range(6))
    return itertools.combinations(wires, size)


def _mcx_exact(q, controls, target, borrowed=()):
    controls = list(controls)
    if not controls:
        q.x(target)
    elif len(controls) == 1:
        q.cx(controls[0], target)
    elif len(controls) == 2:
        q.ccx(*controls, target)
    else:
        # This deliberately uses no borrowed workspace.  A later version will
        # replace this with a genuinely flag-controlled conditional-clean
        # construction; ordinary MCX ancillas cannot safely be dirty outside
        # the active selector branch.
        if borrowed:
            needed = max(0, len(controls) - 2)
            q.mcx(
                controls,
                target,
                ancilla_qubits=list(borrowed)[:needed],
                mode="v-chain-dirty",
            )
        else:
            q.mcx(controls, target, mode="noancilla")


def _toggle_target(q, controls, target, negative=()):
    negative = set(negative)
    for wire in negative:
        q.x(wire)
    _mcx_exact(q, controls, target)
    for wire in negative:
        q.x(wire)


def _phase_cube(q, controls, negative=(), borrowed=()):
    negative = set(negative)
    for wire in negative:
        q.x(wire)
    controls = list(controls)
    if not controls:
        q.global_phase += np.pi
    elif len(controls) == 1:
        q.z(controls[0])
    else:
        target = controls[-1]
        q.h(target)
        _mcx_exact(q, controls[:-1], target, borrowed)
        q.h(target)
    for wire in negative:
        q.x(wire)


def compile_local_branch(selector_bits, selector_assignment: int, conditional_clean=False):
    """Compile one exact branch, without yet borrowing selector wires.

    This is the safe reference implementation for the local-depth experiment.
    It computes the selector flag in q12, applies the residual ESOP directly
    as phase cubes, and restores every wire.  It is intentionally conservative
    so that any improvement from conditional-clean workspace is measurable.
    """
    coordinates = residual_coordinates(selector_bits)
    table = cofactor_table(selector_bits, selector_assignment, coordinates)
    table_int = sum(int(v) << i for i, v in enumerate(table))
    cubes = esop(table_int, len(coordinates))
    q = QuantumCircuit(18)

    selector_wires = [wire if kind == "x" else 6 + wire for kind, wire in selector_bits]
    desired = [(selector_assignment >> i) & 1 for i in range(len(selector_bits))]
    negative = [wire for wire, value in zip(selector_wires, desired) if not value]
    _toggle_target(q, selector_wires, 12, negative)

    borrowed = ()
    if conditional_clean:
        # Selector wires are clean only after the active flag is set.  Every
        # selector bit whose branch value is one is conditionally flipped to
        # zero, and restored after the local phase network.
        for wire, value in zip(selector_wires, desired):
            if value:
                q.cx(12, wire)
        borrowed = tuple([13, 14, 15, 16, 17] + selector_wires)

    residual_wires = [(wire if kind == "x" else 6 + wire) for kind, wire in coordinates]
    for mask, value in cubes:
        controls = [12]
        neg = []
        for i, wire in enumerate(residual_wires):
            if mask >> i & 1:
                controls.append(wire)
                if not (value >> i & 1):
                    neg.append(wire)
        _phase_cube(q, controls, neg, borrowed)

    if conditional_clean:
        for wire, value in reversed(list(zip(selector_wires, desired))):
            if value:
                q.cx(12, wire)

    _toggle_target(q, selector_wires, 12, negative)
    return transpile(
        q,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
        seed_transpiler=0,
    ), {"selector_assignment": selector_assignment, "cubes": len(cubes)}


def _xor_and_segment(left, right, signal_wire, target):
    """Compute target ^= affine(left) & affine(right) over GF(2)."""
    segment = QuantumCircuit(18)
    left = set(left)
    right = set(right)
    singles = set()
    pairs = set()
    for a in left:
        for b in right:
            if a == 0 and b == 0:
                segment.x(target)
            elif a == 0:
                singles.symmetric_difference_update([b])
            elif b == 0:
                singles.symmetric_difference_update([a])
            elif a == b:
                singles.symmetric_difference_update([a])
            else:
                pair = tuple(sorted((a, b)))
                if pair in pairs:
                    pairs.remove(pair)
                else:
                    pairs.add(pair)
    for signal in sorted(singles):
        segment.cx(signal_wire(signal), target)
    for a, b in sorted(pairs):
        segment.rccx(signal_wire(a), signal_wire(b), target)
    return segment


def compile_factored_branch(selector_bits, selector_assignment: int, component="full"):
    """Compile branch 3 as P*G XOR R using a bounded six-variable XAG."""
    if selector_bits != (("x", 5), ("y", 3), ("y", 4), ("y", 5)) or selector_assignment != 3:
        raise ValueError("the first factored pilot is fixed to selector A, assignment 3")
    if component not in {"full", "pg", "r"}:
        raise ValueError("component must be full, pg, or r")
    coordinates = residual_coordinates(selector_bits)
    table = cofactor_table(selector_bits, selector_assignment, coordinates)
    cubes = esop_for_table(table)

    # P is x4=0 AND y2=1.  Seven ESOP cubes contain this signed pair.  After
    # removing P, the exact residual G uses six variables; the remainder R
    # contains six marked inputs and has four ESOP cubes.
    p_indices = (4, 7)
    p_values = (0, 1)
    remaining = [i for i in range(8) if i not in p_indices]
    g = 0
    for mask, value in cubes:
        if not all(mask >> i & 1 and ((value >> i) & 1) == wanted
                   for i, wanted in zip(p_indices, p_values)):
            continue
        rem_mask = rem_value = 0
        for new_i, old_i in enumerate(remaining):
            if mask >> old_i & 1:
                rem_mask |= 1 << new_i
            if value >> old_i & 1:
                rem_value |= 1 << new_i
        for assignment in range(64):
            if (assignment & rem_mask) == (rem_value & rem_mask):
                g ^= 1 << assignment
    expanded = 0
    for assignment in range(256):
        if ((assignment >> 4) & 1) == 0 and ((assignment >> 7) & 1) == 1:
            g_index = sum(((assignment >> old_i) & 1) << new_i
                          for new_i, old_i in enumerate(remaining))
            expanded |= ((g >> g_index) & 1) << assignment
    remainder = sum(int(v) << i for i, v in enumerate(table)) ^ expanded
    remainder_cubes = esop(remainder, 8)

    # Exact six-variable XAG returned by minmc_xag.py for G.  The sixth
    # bounded node is affine (AND with constant one) and is folded into the
    # output, leaving five nonlinear nodes for q13..q17.
    xag_nodes = [
        ((0, 1, 3), (2,)),
        ((3,), (2, 3, 4, 7)),
        ((1, 7, 8), (1, 4, 5)),
        ((1, 3, 6, 9), (0, 1, 2, 8, 9)),
        ((3, 4), (6, 10)),
    ]
    output_signals = {3, 4, 6, 10, 11}
    input_wires = [coordinates[i] for i in remaining]
    input_wires = [wire if kind == "x" else 6 + wire for kind, wire in input_wires]
    node_wires = {7: 13, 8: 14, 9: 15, 10: 16, 11: 17}

    def signal_wire(signal):
        if 1 <= signal <= 6:
            return input_wires[signal - 1]
        if signal in node_wires:
            return node_wires[signal]
        raise ValueError(f"unsupported signal {signal}")

    q = QuantumCircuit(18)
    selector_wires = [wire if kind == "x" else 6 + wire for kind, wire in selector_bits]
    desired = [(selector_assignment >> i) & 1 for i in range(len(selector_bits))]
    negative_selector = [wire for wire, value in zip(selector_wires, desired) if not value]
    _toggle_target(q, selector_wires, 12, negative_selector)
    for wire, value in zip(selector_wires, desired):
        if value:
            q.cx(12, wire)
    # Keep the first factored pilot on the exact no-ancilla phase reference;
    # the XAG reduction is the variable being measured here.
    borrowed = ()

    residual_wires = [wire if kind == "x" else 6 + wire for kind, wire in coordinates]
    segments = []
    if component in {"full", "pg"}:
        for node_index, (left, right) in enumerate(xag_nodes):
            segment = _xor_and_segment(left, right, signal_wire, 13 + node_index)
            q.compose(segment, inplace=True)
            segments.append(segment)
        for signal in sorted(output_signals - {11}):
            q.cx(signal_wire(signal), 17)
        _phase_cube(q, [12, residual_wires[4], residual_wires[7], 17], [residual_wires[4]], borrowed)
        for signal in sorted(output_signals - {11}):
            q.cx(signal_wire(signal), 17)
        for segment in reversed(segments):
            q.compose(segment.inverse(), inplace=True)

    # The XAG workspace is clean again, so the exceptional remainder can use
    # the ordinary ancillas in addition to the conditionally-clean selectors.
    # The exceptional cubes are few but wide; use the exact no-ancilla
    # reference decomposition here until a dedicated dirty-MCZ lowering is
    # available for this control count.
    if component in {"full", "r"}:
        remainder_borrowed = ()
        for mask, value in remainder_cubes:
            controls = [12]
            negative = []
            for i, wire in enumerate(residual_wires):
                if mask >> i & 1:
                    controls.append(wire)
                    if not (value >> i & 1):
                        negative.append(wire)
            _phase_cube(q, controls, negative, remainder_borrowed)
    for wire, value in reversed(list(zip(selector_wires, desired))):
        if value:
            q.cx(12, wire)
    _toggle_target(q, selector_wires, 12, negative_selector)
    out = transpile(q, basis_gates=["u3", "cx"], qubits_initially_zero=False,
                    optimization_level=3, seed_transpiler=0)
    return out, {
        "selector_assignment": selector_assignment,
        "component": component,
        "factor": "x4=0 AND y2=1",
        "g_ones": int(g.bit_count()),
        "remainder_ones": int(remainder.bit_count()),
        "remainder_cubes": len(remainder_cubes),
        "xag_and_nodes": len(xag_nodes),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/conditionally_clean_screen.json")
    parser.add_argument("--compile-assignment", type=int)
    parser.add_argument("--conditional-clean", action="store_true")
    parser.add_argument("--profile-assignment", type=int)
    parser.add_argument("--factored", action="store_true")
    parser.add_argument("--factored-component", choices=["full", "pg", "r"], default="full")
    parser.add_argument("--scan-selector-size", type=int, action="append")
    parser.add_argument("--scan-output", default="artifacts/conditionally_clean_selector_scan.json")
    args = parser.parse_args()
    selectors = [
        (("x", 5), ("y", 5)),
        (("x", 5), ("y", 4), ("y", 5)),
        (("x", 5), ("y", 3), ("y", 4), ("y", 5)),
        (("x", 5), ("y", 2), ("y", 3), ("y", 4), ("y", 5)),
    ]
    result = {"selectors": [analyze_selector(selector) for selector in selectors]}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    for item in result["selectors"]:
        ranks = [branch["xy_rank"] for branch in item["branches"]]
        print(item["selector_bits"], item["nonzero_branches"], item["residual_variables"], ranks)
    if args.compile_assignment is not None:
        selector = selectors[2]
        if args.factored:
            circuit, metadata = compile_factored_branch(
                selector, args.compile_assignment, args.factored_component
            )
            suffix = "factored" if args.factored_component == "full" else f"factored_{args.factored_component}"
        else:
            circuit, metadata = compile_local_branch(
                selector, args.compile_assignment, args.conditional_clean
            )
            suffix = "borrowed" if args.conditional_clean else "safe"
        output = Path(f"artifacts/conditionally_clean_branch_{args.compile_assignment}_{suffix}.qasm")
        output.write_text(qasm2.dumps(circuit))
        print({"output": str(output), "depth": circuit.depth(), "cx": circuit.count_ops().get("cx", 0), **metadata})
    if args.profile_assignment is not None:
        selector = selectors[2]
        coordinates = residual_coordinates(selector)
        table = cofactor_table(selector, args.profile_assignment, coordinates)
        print(json.dumps({"selector": selector, "assignment": args.profile_assignment, **representation_profile(table)}, indent=2))
    if args.scan_selector_size:
        scan = []
        for size in args.scan_selector_size:
            for selector in all_selector_sets(size):
                scan.append(selector_signature(selector))
            print("scanned selector size", size, "count", sum(1 for _ in all_selector_sets(size)), flush=True)
        scan.sort(key=lambda item: (item["classical_factor_score"], item["sum_esop_cubes"], item["nonzero_branches"]))
        scan_path = Path(args.scan_output)
        scan_path.parent.mkdir(parents=True, exist_ok=True)
        scan_path.write_text(json.dumps(scan, indent=2) + "\n")
        print("top selector signatures:")
        for item in scan[:10]:
            print(item["selector_bits"], item["classical_factor_score"], item["sum_esop_cubes"], item["nonzero_branches"])
        print(scan_path)
    print(path)


if __name__ == "__main__":
    main()
