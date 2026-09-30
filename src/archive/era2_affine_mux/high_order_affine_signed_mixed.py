"""Mixed signed/positive correction candidate at forward depth 92."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from qiskit import transpile
from qiskit.circuit.library import RCCXGate, RC3XGate

from destructive_semantic_search import (
    apply_rccx_semantic,
    build_circuit,
    exact_affine_distance,
    initial_wire_truth_tables,
)


BASE = Path(__file__).resolve().parents[1] / "artifacts" / "destructive_semantic" / (
    "double_seed42_b16x6_p4_depth59.json"
)
SIGNED = (11, ((5, False), (7, True), (8, True), (9, False), (15, True)))
POSITIVE = (12, (2, 3, 4, 11))


def signed_value(wires, controls):
    mask = (1 << 4096) - 1
    value = mask
    for wire, positive in controls:
        value &= wires[wire] if positive else mask ^ wires[wire]
    return value


def append_signed_five(circuit, target, controls, clean=17):
    for wire, positive in controls:
        if not positive:
            circuit.x(wire)
    a, b, c, d, e = [wire for wire, _ in controls]
    circuit.append(RC3XGate(), [a, b, c, clean])
    circuit.append(RC3XGate(), [clean, d, e, target])
    circuit.append(RC3XGate(), [a, b, c, clean])
    for wire, positive in reversed(controls):
        if not positive:
            circuit.x(wire)


def append_positive_four(circuit, target, controls, clean=17):
    a, b, c, d = controls
    circuit.append(RCCXGate(), [a, b, clean])
    circuit.append(RC3XGate(), [clean, c, d, target])
    circuit.append(RCCXGate(), [a, b, clean])


def build_chain(base_path: Path = BASE):
    record = json.loads(base_path.read_text())
    gates = tuple(tuple(gate) for gate in record["gates"])
    wires = initial_wire_truth_tables()
    for _, a, b, target in gates:
        wires = apply_rccx_semantic(wires, a, b, target)
    if wires[13] != 0 or wires[17] != 0:
        raise AssertionError("q13 and q17 must both be clean before the chain")

    before, before_combo = exact_affine_distance(wires)
    circuit = build_circuit(gates)
    target, controls = SIGNED
    append_signed_five(circuit, target, controls)
    corrected = list(wires)
    corrected[target] ^= signed_value(corrected, controls)
    target, controls = POSITIVE
    append_positive_four(circuit, target, controls)
    value = corrected[controls[0]]
    for control in controls[1:]:
        value &= corrected[control]
    corrected[target] ^= value
    if corrected[13] != 0 or corrected[17] != 0:
        raise AssertionError("clean ancillas were not restored")
    after, after_combo = exact_affine_distance(tuple(corrected))
    if after != 331:
        raise AssertionError(f"unexpected mixed signed residual: {after}")
    return circuit, {
        "experiment": "mixed signed/positive correction candidate",
        "base_artifact": BASE.name,
        "base_affine_residual": before,
        "base_affine_combo": before_combo,
        "signed_correction": [SIGNED[0], [[wire, positive] for wire, positive in SIGNED[1]]],
        "positive_correction": [POSITIVE[0], list(POSITIVE[1])],
        "corrected_affine_residual": after,
        "corrected_affine_combo": after_combo,
        "semantic_inputs_checked": 4096,
        "clean_ancillas": [13, 17],
        "clean_ancillas_restored": True,
        "classifier_complete": False,
        "oracle_exhaustively_verified": False,
        "status": "depth-screened incomplete classifier candidate",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        circuit, metrics = build_chain()
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
