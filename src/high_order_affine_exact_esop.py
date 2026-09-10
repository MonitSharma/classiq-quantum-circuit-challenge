"""Exact, noncompetitive completion of the v6 destructive classifier.

The v6 affine residual is minimized as a SOP over a reversible 15-wire chart.
Pair/triple cube intersections are then solved over GF(2), producing an exact
ESOP.  Each selected cube is applied to q12 with an MCX; q12 is not a control,
so the correction terms do not change while they are accumulated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from itertools import combinations
from pathlib import Path

from pyeda.inter import espresso_tts, exprvars, truthtable
from qiskit import qasm2, transpile
from qiskit.circuit.library import MCXGate

from destructive_semantic_search import TARGET, initial_wire_truth_tables
from high_order_affine_no_uncompute_v6 import build_candidate_v6


CHART = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16)
MASK = (1 << 4096) - 1


def _replay(circuit):
    wires = list(initial_wire_truth_tables())
    for instruction in circuit.data:
        operation = instruction.operation
        qubits = [circuit.qubits.index(qubit) for qubit in instruction.qubits]
        if operation.name == "x":
            wires[qubits[0]] ^= MASK
        elif operation.name == "rccx":
            wires[qubits[2]] ^= wires[qubits[0]] & wires[qubits[1]]
        elif operation.name == "rcccx":
            wires[qubits[3]] ^= wires[qubits[0]] & wires[qubits[1]] & wires[qubits[2]]
        elif operation.name.startswith("mcx"):
            controls = qubits[:-1]
            target = qubits[-1]
            state = operation.ctrl_state
            cube = MASK
            for bit, wire in enumerate(controls):
                cube &= wires[wire] if (state >> bit) & 1 else MASK ^ wires[wire]
            wires[target] ^= cube
        else:
            raise ValueError(operation.name)
    return wires


def _intersect(left, right):
    positive = left[0] | right[0]
    negative = left[1] | right[1]
    return None if positive & negative else (positive, negative)


def _cube_truth_table(cube, keys):
    positive, negative = cube
    value = 0
    for index, key in enumerate(keys):
        if key & positive == positive and not key & negative:
            value |= 1 << index
    return value


def exact_esop_terms():
    base, _ = build_candidate_v6()
    wires = _replay(base)
    values = ["-"] * (1 << len(CHART))
    keys = []
    for input_index in range(4096):
        key = sum(((wires[wire] >> input_index) & 1) << bit
                  for bit, wire in enumerate(CHART))
        values[key] = str(((TARGET >> input_index) & 1)
                          ^ ((wires[11] >> input_index) & 1)
                          ^ ((wires[12] >> input_index) & 1))
        keys.append(key)

    minimized = espresso_tts(
        truthtable(exprvars("z", len(CHART)), "".join(values))
    )[0]
    sop_cubes = []
    for term in minimized.cover:
        positive = negative = 0
        for literal in term:
            bit = abs(literal.uniqid) - 1
            if literal.uniqid > 0:
                positive |= 1 << bit
            else:
                negative |= 1 << bit
        sop_cubes.append((positive, negative))

    terms = []
    seen = set()
    for order in (1, 2, 3):
        for indices in combinations(range(len(sop_cubes)), order):
            cube = sop_cubes[indices[0]]
            for index in indices[1:]:
                cube = _intersect(cube, sop_cubes[index])
                if cube is None:
                    break
            if cube is not None and cube not in seen:
                seen.add(cube)
                terms.append((cube, _cube_truth_table(cube, keys)))

    target = 0
    for index, input_index in enumerate(range(4096)):
        target |= (((TARGET >> input_index) & 1)
                   ^ ((wires[11] >> input_index) & 1)
                   ^ ((wires[12] >> input_index) & 1)) << index

    basis = {}
    for term_index, (_, value) in enumerate(terms):
        representation = 1 << term_index
        while value:
            pivot = (value & -value).bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot][0]
                representation ^= basis[pivot][1]
            else:
                basis[pivot] = (value, representation)
                break

    value = target
    representation = 0
    while value:
        pivot = (value & -value).bit_length() - 1
        if pivot not in basis:
            raise AssertionError("residual is not in the generated ESOP span")
        value ^= basis[pivot][0]
        representation ^= basis[pivot][1]
    return [terms[index][0] for index in range(len(terms))
            if representation >> index & 1]


def build_exact_classifier():
    circuit, metrics = build_candidate_v6()
    terms = exact_esop_terms()
    for positive, negative in terms:
        controls = []
        control_state = 0
        for bit, wire in enumerate(CHART):
            if (positive | negative) >> bit & 1:
                if positive >> bit & 1:
                    control_state |= 1 << len(controls)
                controls.append(wire)
        circuit.append(
            MCXGate(len(controls), ctrl_state=control_state),
            controls + [12],
        )

    wires = _replay(circuit)
    if wires[11] ^ wires[12] != TARGET:
        raise AssertionError("exact ESOP classifier replay failed")
    metrics = dict(metrics)
    metrics.update({
        "experiment": "exact no-uncompute ESOP completion",
        "esop_terms": len(terms),
        "esop_chart_wires": list(CHART),
        "esop_max_controls": max(
            positive.bit_count() + negative.bit_count()
            for positive, negative in terms
        ),
        "corrected_affine_residual": 0,
        "target_wire": 12,
        "semantic_inputs_checked": 4096,
        "midpoint_garbage_wires": [13, 14, 16, 17],
        "classifier_complete": True,
        "oracle_exhaustively_verified": False,
        "status": "exact classifier; noncompetitive ESOP completion",
    })
    return circuit, metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-qasm", type=Path)
    parser.add_argument("--out-metrics", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        circuit, metrics = build_exact_classifier()
        compiled = transpile(
            circuit,
            basis_gates=["u3", "cx"],
            qubits_initially_zero=False,
            optimization_level=3,
        )
    metrics.update({
        "compiled_forward_depth": compiled.depth(),
        "compiled_forward_cx": compiled.count_ops().get("cx", 0),
        "transpilation": {
            "basis_gates": ["u3", "cx"],
            "qubits_initially_zero": False,
            "optimization_level": 3,
        },
    })
    if args.out_qasm is not None:
        args.out_qasm.parent.mkdir(parents=True, exist_ok=True)
        args.out_qasm.write_text(qasm2.dumps(compiled))
        metrics["qasm_sha256"] = hashlib.sha256(args.out_qasm.read_bytes()).hexdigest()
    if args.out_metrics is not None:
        args.out_metrics.parent.mkdir(parents=True, exist_ok=True)
        args.out_metrics.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
