"""Reordered signed-control continuation with residual 287."""

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


BASE = Path(__file__).resolve().parents[1] / "artifacts" / "destructive_semantic" / (
    "double_seed42_b16x6_p4_depth59.json"
)
SIGNED_FIRST = (11, ((5, False), (7, True), (8, True), (9, False), (15, True)))
SIGNED_SECOND = (11, ((5, False), (6, True), (8, True), (9, True), (10, True), (15, False)))
POSITIVE_LAST = (12, (2, 3, 4, 11))


def signed_value(wires, controls):
    mask = (1 << 4096) - 1
    value = mask
    for wire, positive in controls:
        value &= wires[wire] if positive else mask ^ wires[wire]
    return value


def append_signed(circuit, target, controls, clean_a=17, clean_b=13):
    for wire, positive in controls:
        if not positive:
            circuit.x(wire)
    wires = [wire for wire, _ in controls]
    if len(wires) == 5:
        a, b, c, d, e = wires
        circuit.append(RC3XGate(), [a, b, c, clean_a])
        circuit.append(RC3XGate(), [clean_a, d, e, target])
        circuit.append(RC3XGate(), [a, b, c, clean_a])
    else:
        a, b, c, d, e, f = wires
        circuit.append(RC3XGate(), [a, b, c, clean_a])
        circuit.append(RC3XGate(), [d, e, f, clean_b])
        circuit.append(RCCXGate(), [clean_a, clean_b, target])
        circuit.append(RC3XGate(), [d, e, f, clean_b])
        circuit.append(RC3XGate(), [a, b, c, clean_a])
    for wire, positive in reversed(controls):
        if not positive:
            circuit.x(wire)


def append_positive_four(circuit, target, controls, clean=17):
    a, b, c, d = controls
    circuit.append(RCCXGate(), [a, b, clean])
    circuit.append(RC3XGate(), [clean, c, d, target])
    circuit.append(RCCXGate(), [a, b, clean])


def build_candidate(base_path: Path = BASE):
    record = json.loads(base_path.read_text())
    gates = tuple(tuple(gate) for gate in record["gates"])
    wires = list(initial_wire_truth_tables())
    for _, a, b, target in gates:
        wires = list(apply_rccx_semantic(tuple(wires), a, b, target))
    if wires[13] != 0 or wires[17] != 0:
        raise AssertionError("q13 and q17 must be clean before the chain")
    before, before_combo = exact_affine_distance(tuple(wires))
    circuit = __import__("destructive_semantic_search").build_circuit(gates)
    for target, controls in (SIGNED_FIRST, SIGNED_SECOND):
        append_signed(circuit, target, controls)
        wires[target] ^= signed_value(wires, controls)
    target, controls = POSITIVE_LAST
    append_positive_four(circuit, target, controls)
    value = wires[controls[0]]
    for control in controls[1:]:
        value &= wires[control]
    wires[target] ^= value
    after, after_combo = exact_affine_distance(tuple(wires))
    if after != 287 or wires[13] != 0 or wires[17] != 0:
        raise AssertionError("unexpected reordered signed residual")
    return circuit, {
        "experiment": "reordered signed-control continuation",
        "base_artifact": BASE.name,
        "base_affine_residual": before,
        "base_affine_combo": before_combo,
        "corrections": [
            [target, [[wire, positive] for wire, positive in controls]]
            for target, controls in (SIGNED_FIRST, SIGNED_SECOND)
        ] + [[POSITIVE_LAST[0], list(POSITIVE_LAST[1])]],
        "corrected_affine_residual": after,
        "corrected_affine_combo": after_combo,
        "semantic_inputs_checked": 4096,
        "clean_ancillas": [13, 17],
        "clean_ancillas_restored": True,
        "classifier_complete": False,
        "oracle_exhaustively_verified": False,
        "status": "signed semantic Pareto continuation; above depth screen",
    }


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
    })
    print(json.dumps(metrics, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
