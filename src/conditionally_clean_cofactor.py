"""Conditionally-clean cofactor experiments.

The first version deliberately keeps the classical analysis separate from the
quantum compiler.  It is intended to make the selector trade-off reproducible
before any complete-oracle integration is attempted.
"""

from __future__ import annotations

import argparse
import itertools
import json
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/conditionally_clean_screen.json")
    parser.add_argument("--compile-assignment", type=int)
    parser.add_argument("--conditional-clean", action="store_true")
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
        circuit, metadata = compile_local_branch(
            selector, args.compile_assignment, args.conditional_clean
        )
        suffix = "borrowed" if args.conditional_clean else "safe"
        output = Path(f"artifacts/conditionally_clean_branch_{args.compile_assignment}_{suffix}.qasm")
        output.write_text(qasm2.dumps(circuit))
        print({"output": str(output), "depth": circuit.depth(), "cx": circuit.count_ops().get("cx", 0), **metadata})
    print(path)


if __name__ == "__main__":
    main()
