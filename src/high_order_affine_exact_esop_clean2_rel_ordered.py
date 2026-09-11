"""Ordered 83-cube relative-phase two-clean destructive oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from pathlib import Path

from qiskit import qasm2, transpile
from qiskit.circuit.library import MCXGate

from destructive_semantic_search import TARGET
from high_order_affine_exact_esop import CHART
from high_order_affine_exact_esop_clean1 import _replay
from high_order_affine_exact_esop_clean2_rel import (
    _clear_q13, _clear_q17, _relative_clean2_gate, _restore_q17,
)
from high_order_affine_exact_esop_clean2_rel_alt import _terms_alt
from high_order_affine_no_uncompute_v6 import build_candidate_v6


def _ordered_terms():
    """Greedy shared-literal order, starting from the third cube."""
    remaining = list(_terms_alt())
    current = remaining.pop(2)
    ordered = [current]
    while remaining:
        positive, negative = current

        def key(term):
            other_positive, other_negative = term
            # The second key is intentionally a control/polarity tie-break;
            # the resulting order is fixed for the installed Espresso cover.
            return (
                (positive ^ other_positive).bit_count()
                + (negative ^ other_negative).bit_count(),
                ((positive ^ other_positive)
                 | (negative ^ other_positive)).bit_count(),
            )

        current = min(remaining, key=key)
        remaining.remove(current)
        ordered.append(current)
    return tuple(ordered)


def _append_cube(circuit, positive: int, negative: int) -> None:
    controls = []
    control_state = 0
    for bit, wire in enumerate(CHART):
        if (positive | negative) >> bit & 1:
            if positive >> bit & 1:
                control_state |= 1 << len(controls)
            controls.append(wire)
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
    if _replay(circuit)[13] != 0 or _replay(circuit)[17] != 0:
        raise AssertionError("two-wire clean-up failed")
    terms = _ordered_terms()
    for positive, negative in terms:
        _append_cube(circuit, positive, negative)
    _restore_q17(circuit)
    _clear_q13(circuit)
    circuit.cx(11, 12)
    wires = _replay(circuit)
    if wires[12] != TARGET or wires[13] != base_wires[13] or wires[17] != base_wires[17]:
        raise AssertionError("ordered classifier replay failed")
    metrics = dict(metrics)
    metrics.update({
        "experiment": "ordered 83-cube relative-phase two-clean completion",
        "esop_terms": len(terms),
        "esop_chart_wires": list(CHART),
        "esop_cover_warmup_calls": 1,
        "esop_order": "greedy shared-literal start index 2",
        "mcx_synthesis": "synth_mcx_2_clean_kg24 with middle CCX -> RCCX",
        "clean_ancillas": [13, 17],
        "relative_phase_internal": True,
        "corrected_affine_residual": 0,
        "target_wire": 12,
        "semantic_inputs_checked": 4096,
        "classifier_complete": True,
        "oracle_exhaustively_verified": False,
        "status": "exact classifier; ordered 83-cube candidate",
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
