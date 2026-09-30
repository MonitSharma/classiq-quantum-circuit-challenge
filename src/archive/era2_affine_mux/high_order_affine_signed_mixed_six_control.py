"""Residual-295 continuation from the depth-92 mixed signed candidate."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from qiskit import transpile
from qiskit.circuit.library import RCCXGate, RC3XGate

from destructive_semantic_search import (
    apply_rccx_semantic,
    exact_affine_distance,
    initial_wire_truth_tables,
)
from high_order_affine_signed_mixed import build_chain as build_mixed_chain


CORRECTION = (11, ((4, False), (5, True), (8, True), (9, True), (10, False), (16, False)))


def signed_value(wires, controls):
    mask = (1 << 4096) - 1
    value = mask
    for wire, positive in controls:
        value &= wires[wire] if positive else mask ^ wires[wire]
    return value


def append_signed_six(circuit, target, controls, clean_a=17, clean_b=13):
    for wire, positive in controls:
        if not positive:
            circuit.x(wire)
    a, b, c, d, e, f = [wire for wire, _ in controls]
    circuit.append(RC3XGate(), [a, b, c, clean_a])
    circuit.append(RC3XGate(), [d, e, f, clean_b])
    circuit.append(RCCXGate(), [clean_a, clean_b, target])
    circuit.append(RC3XGate(), [d, e, f, clean_b])
    circuit.append(RC3XGate(), [a, b, c, clean_a])
    for wire, positive in reversed(controls):
        if not positive:
            circuit.x(wire)


def build_candidate():
    circuit, metrics = build_mixed_chain()
    # Reconstruct the semantic state at the mixed-chain midpoint independently.
    base = Path(__file__).resolve().parents[1] / "artifacts" / "destructive_semantic" / (
        "double_seed42_b16x6_p4_depth59.json"
    )
    record = json.loads(base.read_text())
    wires = list(initial_wire_truth_tables())
    for _, a, b, target in record["gates"]:
        wires = list(apply_rccx_semantic(tuple(wires), a, b, target))
    signed = ((5, False), (7, True), (8, True), (9, False), (15, True))
    wires[11] ^= signed_value(wires, signed)
    positive = (2, 3, 4, 11)
    value = wires[positive[0]]
    for control in positive[1:]:
        value &= wires[control]
    wires[12] ^= value

    target, controls = CORRECTION
    append_signed_six(circuit, target, controls)
    wires[target] ^= signed_value(wires, controls)
    after, combo = exact_affine_distance(tuple(wires))
    if after != 295 or wires[13] != 0 or wires[17] != 0:
        raise AssertionError("unexpected residual-295 continuation")
    metrics = dict(metrics)
    metrics.update({
        "experiment": "residual-295 signed six-control continuation",
        "additional_correction": [target, [[wire, positive] for wire, positive in controls]],
        "corrected_affine_residual": after,
        "corrected_affine_combo": combo,
        "clean_ancillas_restored": True,
        "status": "semantic Pareto continuation; above promising depth screen",
    })
    return circuit, metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        circuit, metrics = build_candidate()
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
        "classifier_complete": False,
        "oracle_exhaustively_verified": False,
    })
    print(json.dumps(metrics, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
