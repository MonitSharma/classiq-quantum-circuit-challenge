"""Exact v6 classifier with a two-borrowed-ancilla MCX lowering.

This is a separate candidate from ``high_order_affine_exact_esop``.  The
Khattar--Gidney two-dirty-ancilla synthesis uses only RCCX/CCX primitives, so
it remains a monomial reversible classifier while borrowing two wires that are
not controls for each ESOP cube.  The borrowed wires are restored by the
synthesis itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from functools import lru_cache
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import MCXGate
from qiskit.synthesis import synth_mcx_2_dirty_kg24

from destructive_semantic_search import TARGET, initial_wire_truth_tables
from high_order_affine_exact_esop import CHART, exact_esop_terms
from high_order_affine_no_uncompute_v6 import build_candidate_v6


MASK = (1 << 4096) - 1


@lru_cache(maxsize=1)
def _terms():
    """Freeze the lower-cost second exact cover for consistent rebuilds."""
    exact_esop_terms()  # warm-up cover; retain one selected cover below
    return tuple(exact_esop_terms())


def _replay(circuit: QuantumCircuit) -> list[int]:
    wires = list(initial_wire_truth_tables())
    for instruction in circuit.data:
        operation = instruction.operation
        qubits = [circuit.qubits.index(qubit) for qubit in instruction.qubits]
        if operation.name == "x":
            wires[qubits[0]] ^= MASK
        elif operation.name == "cx":
            wires[qubits[1]] ^= wires[qubits[0]]
        elif operation.name in {"rccx", "ccx"}:
            wires[qubits[-1]] ^= wires[qubits[0]] & wires[qubits[1]]
        elif operation.name == "rcccx":
            wires[qubits[3]] ^= (
                wires[qubits[0]] & wires[qubits[1]] & wires[qubits[2]]
            )
        elif operation.name.startswith("mcx"):
            controls, target = qubits[:-1], qubits[-1]
            cube = MASK
            for index, control in enumerate(controls):
                cube &= (wires[control] if operation.ctrl_state >> index & 1
                         else MASK ^ wires[control])
            wires[target] ^= cube
        else:
            raise ValueError(f"unsupported semantic operation: {operation.name}")
    return wires


def _append_cube(circuit: QuantumCircuit, positive: int, negative: int) -> None:
    controls = []
    control_state = 0
    for bit, wire in enumerate(CHART):
        if (positive | negative) >> bit & 1:
            if positive >> bit & 1:
                control_state |= 1 << len(controls)
            controls.append(wire)
    ancillas = [
        wire for wire in range(18)
        if wire != 12 and wire not in controls
    ][:2]
    for index, wire in enumerate(controls):
        if not (control_state >> index) & 1:
            circuit.x(wire)
    if len(controls) >= 3:
        # The synthesis has n controls, one target, and two borrowed wires.
        circuit.compose(
            synth_mcx_2_dirty_kg24(len(controls)),
            qubits=controls + [12] + ancillas,
            inplace=True,
        )
    else:
        circuit.append(MCXGate(len(controls)), controls + [12])
    for index, wire in enumerate(controls):
        if not (control_state >> index) & 1:
            circuit.x(wire)


def build_classifier():
    circuit, metrics = build_candidate_v6()
    terms = _terms()
    for positive, negative in terms:
        _append_cube(circuit, positive, negative)
    circuit.cx(11, 12)
    wires = _replay(circuit)
    if wires[12] != TARGET:
        raise AssertionError("dirty-ancilla ESOP classifier replay failed")
    metrics = dict(metrics)
    metrics.update({
        "experiment": "exact ESOP completion with two borrowed ancillas",
        "esop_terms": len(terms),
        "esop_chart_wires": list(CHART),
        "dirty_mcx_synthesis": "synth_mcx_2_dirty_kg24",
        "dirty_ancillas_per_cube": 2,
        "corrected_affine_residual": 0,
        "target_wire": 12,
        "semantic_inputs_checked": 4096,
        "classifier_complete": True,
        "oracle_exhaustively_verified": False,
        "status": "exact classifier; dirty-ancilla lowering candidate",
    })
    return circuit, metrics


def build_oracle():
    classifier, metrics = build_classifier()
    oracle = classifier.copy()
    oracle.z(12)
    oracle.compose(classifier.inverse(), inplace=True)
    return oracle, metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-qasm", type=Path)
    parser.add_argument("--out-oracle-qasm", type=Path)
    parser.add_argument("--out-metrics", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        classifier, metrics = build_classifier()
        compiled = transpile(
            classifier, basis_gates=["u3", "cx"],
            qubits_initially_zero=False, optimization_level=3,
            seed_transpiler=0,
        )
    metrics.update({
        "compiled_forward_depth": compiled.depth(),
        "compiled_forward_cx": compiled.count_ops().get("cx", 0),
        "transpilation": {
            "basis_gates": ["u3", "cx"],
            "qubits_initially_zero": False,
            "optimization_level": 3,
            "seed_transpiler": 0,
        },
    })
    if args.out_qasm is not None:
        args.out_qasm.parent.mkdir(parents=True, exist_ok=True)
        args.out_qasm.write_text(qasm2.dumps(compiled))
        metrics["qasm_sha256"] = hashlib.sha256(
            args.out_qasm.read_bytes()
        ).hexdigest()
    if args.out_oracle_qasm is not None:
        oracle, _ = build_oracle()
        oracle_compiled = transpile(
            oracle, basis_gates=["u3", "cx"],
            qubits_initially_zero=False, optimization_level=3,
            seed_transpiler=0,
        )
        args.out_oracle_qasm.parent.mkdir(parents=True, exist_ok=True)
        args.out_oracle_qasm.write_text(qasm2.dumps(oracle_compiled))
        metrics.update({
            "oracle_depth": oracle_compiled.depth(),
            "oracle_cx": oracle_compiled.count_ops().get("cx", 0),
            "oracle_qasm_sha256": hashlib.sha256(
                args.out_oracle_qasm.read_bytes()
            ).hexdigest(),
        })
    if args.out_metrics is not None:
        args.out_metrics.parent.mkdir(parents=True, exist_ok=True)
        args.out_metrics.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
