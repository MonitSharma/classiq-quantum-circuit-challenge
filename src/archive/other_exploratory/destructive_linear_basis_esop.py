"""Destructive ESOP completion after an invertible CNOT basis change.

The v6 semantic prefix is unchanged.  Before the exact residual ESOP is
applied, a short invertible CNOT network changes the Boolean basis of the
non-target chart wires; its inverse is applied immediately afterward.  This
is a reversible coordinate change, not an input-preserving architecture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from functools import lru_cache
from itertools import combinations
from pathlib import Path

from pyeda.inter import espresso_tts, exprvars, truthtable
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import MCXGate

from destructive_semantic_search import TARGET
from high_order_affine_exact_esop import CHART, _replay
from high_order_affine_exact_esop_clean2_rel import (
    _clear_q13,
    _clear_q17,
    _relative_clean2_gate,
    _restore_q17,
)
from high_order_affine_no_uncompute_v6 import build_candidate_v6


# This sequence is a fixed invertible CNOT walk over chart wires other than
# q11.  q11 is deliberately untouched because it supplies the final affine
# q11 -> q12 completion tail.
BASIS_CNOTS = ((7, 9), (5, 10), (8, 7), (9, 7), (15, 1), (16, 9))
MASK = (1 << 4096) - 1


def _intersect(left: tuple[int, int], right: tuple[int, int]):
    positive = left[0] | right[0]
    negative = left[1] | right[1]
    return None if positive & negative else (positive, negative)


@lru_cache(maxsize=1)
def exact_terms() -> tuple[tuple[int, int], ...]:
    base, _ = build_candidate_v6()
    wires = _replay(base)
    transformed = list(wires)
    for source, target in BASIS_CNOTS:
        transformed[target] ^= transformed[source]

    values = ["-"] * (1 << len(CHART))
    keys: list[int] = []
    desired: list[int] = []
    for input_index in range(4096):
        key = sum(
            ((transformed[wire] >> input_index) & 1) << bit
            for bit, wire in enumerate(CHART)
        )
        value = (
            ((TARGET >> input_index) & 1)
            ^ ((wires[11] >> input_index) & 1)
            ^ ((wires[12] >> input_index) & 1)
        )
        values[key] = str(value)
        keys.append(key)
        desired.append(value)

    minimized = espresso_tts(
        truthtable(exprvars("z", len(CHART)), "".join(values))
    )[0]
    sop: list[tuple[int, int]] = []
    for term in minimized.cover:
        positive = negative = 0
        for literal in term:
            bit = abs(literal.uniqid) - 1
            if literal.uniqid > 0:
                positive |= 1 << bit
            else:
                negative |= 1 << bit
        sop.append((positive, negative))
    sop.sort()

    pool: list[tuple[tuple[int, int], int]] = []
    seen: set[tuple[int, int]] = set()
    for order in (1, 2, 3):
        for indices in combinations(range(len(sop)), order):
            cube = sop[indices[0]]
            for index in indices[1:]:
                cube = _intersect(cube, sop[index])
                if cube is None:
                    break
            if cube is None or cube in seen:
                continue
            seen.add(cube)
            cube_value = 0
            positive, negative = cube
            for index, key in enumerate(keys):
                if key & positive == positive and not key & negative:
                    cube_value |= 1 << index
            pool.append((cube, cube_value))

    target = sum(value << index for index, value in enumerate(desired))
    basis: dict[int, tuple[int, int]] = {}
    for term_index, (_, value0) in enumerate(pool):
        value = value0
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
            raise AssertionError("basis-change residual is not in ESOP span")
        value ^= basis[pivot][0]
        representation ^= basis[pivot][1]
    return tuple(
        pool[index][0]
        for index in range(len(pool))
        if representation >> index & 1
    )


def _append_cube(circuit: QuantumCircuit, positive: int, negative: int) -> None:
    controls: list[int] = []
    control_state = 0
    for bit, wire in enumerate(CHART):
        if (positive | negative) >> bit & 1:
            if positive >> bit & 1:
                control_state |= 1 << len(controls)
            controls.append(wire)
    if 12 in controls or 13 in controls or 17 in controls:
        raise AssertionError("basis-change ESOP used a forbidden workspace wire")
    for index, wire in enumerate(controls):
        if not (control_state >> index) & 1:
            circuit.x(wire)
    if len(controls) >= 3:
        circuit.compose(
            _relative_clean2_gate(len(controls)),
            controls + [12, 13, 17],
            inplace=True,
        )
    else:
        circuit.append(MCXGate(len(controls), ctrl_state=control_state), controls + [12])
    for index, wire in enumerate(controls):
        if not (control_state >> index) & 1:
            circuit.x(wire)


def build_classifier(terms: tuple[tuple[int, int], ...] | None = None):
    circuit, metrics = build_candidate_v6()
    base_wires = _replay(circuit)
    _clear_q13(circuit)
    _clear_q17(circuit)
    for source, target in BASIS_CNOTS:
        circuit.cx(source, target)
    for positive, negative in terms or exact_terms():
        _append_cube(circuit, positive, negative)
    for source, target in reversed(BASIS_CNOTS):
        circuit.cx(source, target)
    _restore_q17(circuit)
    _clear_q13(circuit)
    circuit.cx(11, 12)
    wires = _replay(circuit)
    if wires[12] != TARGET or wires[13] != base_wires[13] or wires[17] != base_wires[17]:
        raise AssertionError("basis-change classifier replay failed")
    metrics = dict(metrics)
    terms = terms or exact_terms()
    metrics.update({
        "experiment": "destructive ESOP with invertible CNOT basis change",
        "basis_cnot_sequence": [list(pair) for pair in BASIS_CNOTS],
        "esop_terms": len(terms),
        "esop_literals": sum(p.bit_count() + n.bit_count() for p, n in terms),
        "target_wire": 12,
        "semantic_inputs_checked": 4096,
        "classifier_complete": True,
        "oracle_exhaustively_verified": False,
    })
    return circuit, metrics


def build_oracle(terms: tuple[tuple[int, int], ...] | None = None):
    classifier, metrics = build_classifier(terms)
    oracle = classifier.copy()
    oracle.z(12)
    oracle.compose(classifier.inverse(), inplace=True)
    return oracle, metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-oracle-qasm", type=Path, required=True)
    parser.add_argument("--out-metrics", type=Path, required=True)
    args = parser.parse_args()
    classifier, metrics = build_classifier()
    compiled = transpile(
        classifier,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
        seed_transpiler=0,
    )
    oracle, _ = build_oracle()
    oracle_compiled = transpile(
        oracle,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
        seed_transpiler=0,
    )
    args.out_oracle_qasm.parent.mkdir(parents=True, exist_ok=True)
    args.out_oracle_qasm.write_text(qasm2.dumps(oracle_compiled))
    metrics.update({
        "compiled_forward_depth": compiled.depth(),
        "compiled_forward_cx": compiled.count_ops().get("cx", 0),
        "oracle_depth": oracle_compiled.depth(),
        "oracle_cx": oracle_compiled.count_ops().get("cx", 0),
        "oracle_qasm_sha256": hashlib.sha256(args.out_oracle_qasm.read_bytes()).hexdigest(),
        "transpilation": {
            "basis_gates": ["u3", "cx"],
            "qubits_initially_zero": False,
            "optimization_level": 3,
            "seed_transpiler": 0,
        },
    })
    args.out_metrics.parent.mkdir(parents=True, exist_ok=True)
    args.out_metrics.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
