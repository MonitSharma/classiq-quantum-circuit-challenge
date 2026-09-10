"""Two-clean destructive ESOP lowering with relative-phase mid-CCX blocks."""

from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import MCXGate, RCCXGate
from qiskit.synthesis import synth_mcx_2_clean_kg24

from destructive_semantic_search import TARGET
from high_order_affine_exact_esop import CHART
from high_order_affine_exact_esop_clean1 import _replay, _terms
from high_order_affine_no_uncompute_v6 import build_candidate_v6


def _relative_clean2_gate(control_count: int) -> QuantumCircuit:
    """Replace the one exact middle CCX by RCCX; Boolean action is unchanged."""
    source = synth_mcx_2_clean_kg24(control_count)
    result = QuantumCircuit(source.num_qubits)
    for instruction in source.data:
        qubits = [source.qubits.index(qubit) for qubit in instruction.qubits]
        if instruction.operation.name == "ccx":
            result.append(RCCXGate(), qubits)
        else:
            result.append(instruction.operation, qubits)
    return result


def _clear_q13(circuit) -> None:
    for wire in (3, 4):
        circuit.x(wire)
    circuit.rccx(3, 4, 13)
    for wire in (4, 3):
        circuit.x(wire)
    circuit.rccx(2, 3, 13)


def _clear_q17(circuit) -> None:
    circuit.rccx(8, 9, 17)
    circuit.x(5)
    circuit.rcccx(5, 7, 8, 17)
    circuit.x(5)


def _restore_q17(circuit) -> None:
    circuit.x(5)
    circuit.rcccx(5, 7, 8, 17)
    circuit.x(5)
    circuit.rccx(8, 9, 17)


def _append_cube(circuit, positive: int, negative: int) -> None:
    controls = []
    control_state = 0
    for bit, wire in enumerate(CHART):
        if (positive | negative) >> bit & 1:
            if positive >> bit & 1:
                control_state |= 1 << len(controls)
            controls.append(wire)
    if 12 in controls or 13 in controls or 17 in controls:
        raise AssertionError("clean workspace entered the ESOP chart")
    for index, wire in enumerate(controls):
        if not (control_state >> index) & 1:
            circuit.x(wire)
    if len(controls) >= 3:
        circuit.compose(
            _relative_clean2_gate(len(controls)),
            qubits=controls + [12, 13, 17],
            inplace=True,
        )
    else:
        circuit.append(MCXGate(len(controls)), controls + [12])
    for index, wire in enumerate(controls):
        if not (control_state >> index) & 1:
            circuit.x(wire)


def build_classifier():
    circuit, metrics = build_candidate_v6()
    base_wires = _replay(circuit)
    _clear_q13(circuit)
    _clear_q17(circuit)
    clean_wires = _replay(circuit)
    if clean_wires[13] != 0 or clean_wires[17] != 0:
        raise AssertionError("two-wire clean-up failed")
    for positive, negative in _terms():
        _append_cube(circuit, positive, negative)
    _restore_q17(circuit)
    _clear_q13(circuit)
    circuit.cx(11, 12)
    wires = _replay(circuit)
    if wires[12] != TARGET or wires[13] != base_wires[13] or wires[17] != base_wires[17]:
        raise AssertionError("relative-phase clean ESOP classifier replay failed")
    metrics = dict(metrics)
    metrics.update({
        "experiment": "exact ESOP two-clean completion with relative-phase mid-CCX",
        "esop_terms": len(_terms()),
        "esop_chart_wires": list(CHART),
        "mcx_synthesis": "synth_mcx_2_clean_kg24 with middle CCX -> RCCX",
        "clean_ancillas": [13, 17],
        "relative_phase_internal": True,
        "corrected_affine_residual": 0,
        "target_wire": 12,
        "semantic_inputs_checked": 4096,
        "classifier_complete": True,
        "oracle_exhaustively_verified": False,
        "status": "exact classifier; relative-phase two-clean lowering candidate",
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
