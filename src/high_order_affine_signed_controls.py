"""Signed-control continuation from the shallow destructive base."""

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
# Each pair is (wire, positive-control flag). Negative controls are surrounded
# by X gates and therefore restore the current semantic wire exactly.
CORRECTIONS = (
    (11, ((5, False), (7, True), (8, True), (9, False), (15, True))),
    (11, ((4, False), (5, True), (8, True), (9, True), (10, False), (16, False))),
)


def signed_value(wires, controls):
    mask = (1 << 4096) - 1
    value = mask
    for wire, positive in controls:
        value &= wires[wire] if positive else mask ^ wires[wire]
    return value


def append_signed_mcx(circuit, target, controls, clean_a=17, clean_b=13):
    if target in [wire for wire, _ in controls]:
        raise ValueError("target cannot also be a control")
    for wire, positive in controls:
        if not positive:
            circuit.x(wire)
    wires = [wire for wire, _ in controls]
    if len(wires) == 5:
        a, b, c, d, e = wires
        circuit.append(RC3XGate(), [a, b, c, clean_a])
        circuit.append(RC3XGate(), [clean_a, d, e, target])
        circuit.append(RC3XGate(), [a, b, c, clean_a])
    elif len(wires) == 6:
        a, b, c, d, e, f = wires
        circuit.append(RC3XGate(), [a, b, c, clean_a])
        circuit.append(RC3XGate(), [d, e, f, clean_b])
        circuit.append(RCCXGate(), [clean_a, clean_b, target])
        circuit.append(RC3XGate(), [d, e, f, clean_b])
        circuit.append(RC3XGate(), [a, b, c, clean_a])
    else:
        raise ValueError("signed helper supports five or six controls")
    for wire, positive in reversed(controls):
        if not positive:
            circuit.x(wire)


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
    corrected = list(wires)
    for target, controls in CORRECTIONS:
        append_signed_mcx(circuit, target, controls)
        corrected[target] ^= signed_value(corrected, controls)
    if corrected[13] != 0 or corrected[17] != 0:
        raise AssertionError("clean ancillas were not restored")
    after, after_combo = exact_affine_distance(tuple(corrected))
    if after != 347:
        raise AssertionError(f"unexpected signed-chain residual: {after}")
    return circuit, {
        "experiment": "signed-control continuation from shallow destructive base",
        "base_artifact": BASE.name,
        "base_affine_residual": before,
        "base_affine_combo": before_combo,
        "corrections": [
            [target, [[wire, positive] for wire, positive in controls]]
            for target, controls in CORRECTIONS
        ],
        "corrected_affine_residual": after,
        "corrected_affine_combo": after_combo,
        "semantic_inputs_checked": 4096,
        "clean_ancillas": [13, 17],
        "clean_ancillas_restored": True,
        "classifier_complete": False,
        "oracle_exhaustively_verified": False,
        "status": "signed-control Pareto candidate; incomplete classifier",
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
