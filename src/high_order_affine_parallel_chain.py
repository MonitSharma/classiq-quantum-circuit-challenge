"""Parallel-clean-ancilla version of the depth-screened affine chain."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from qiskit import QuantumCircuit, transpile
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


def build_parallel_chain(base_path: Path = BASE):
    record = json.loads(base_path.read_text())
    gates = tuple(tuple(gate) for gate in record["gates"])
    wires = initial_wire_truth_tables()
    for _, a, b, target in gates:
        wires = apply_rccx_semantic(wires, a, b, target)
    if wires[13] != 0 or wires[17] != 0:
        raise AssertionError("q13 and q17 must both be clean in the base candidate")
    before, before_combo = exact_affine_distance(wires)

    circuit = build_circuit(gates)
    # First correction product q2&q3&q4 is held in q17; the second q7&q8 is
    # held in q13.  The disjoint compute/uncompute halves can be scheduled in
    # parallel.  The target toggles share q12 and remain sequential.
    circuit.append(RC3XGate(), [2, 3, 4, 17])
    circuit.append(RCCXGate(), [7, 8, 13])
    circuit.append(RC3XGate(), [17, 8, 11, 12])
    circuit.append(RC3XGate(), [13, 10, 11, 12])
    circuit.append(RC3XGate(), [2, 3, 4, 17])
    circuit.append(RCCXGate(), [7, 8, 13])
    # Third correction q11 ^= q5&q8&q10&q12, using restored q17.
    circuit.append(RCCXGate(), [5, 8, 17])
    circuit.append(RC3XGate(), [17, 10, 12, 11])
    circuit.append(RCCXGate(), [5, 8, 17])

    corrected = list(wires)
    for target, controls in (
        (12, (2, 3, 4, 8, 11)),
        (12, (7, 8, 10, 11)),
        (11, (5, 8, 10, 12)),
    ):
        value = corrected[controls[0]]
        for control in controls[1:]:
            value &= corrected[control]
        corrected[target] ^= value
    if corrected[13] != 0 or corrected[17] != 0:
        raise AssertionError("clean ancillas were not restored")
    after, after_combo = exact_affine_distance(tuple(corrected))
    if after != 339:
        raise AssertionError(f"unexpected parallel-chain residual: {after}")
    return circuit, {
        "base_affine_residual": before,
        "base_affine_combo": before_combo,
        "corrected_affine_residual": after,
        "corrected_affine_combo": after_combo,
        "semantic_inputs_checked": 4096,
        "clean_ancillas": [13, 17],
        "clean_ancillas_restored": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        circuit, metrics = build_parallel_chain()
        compiled = transpile(circuit, basis_gates=["u3", "cx"],
                             qubits_initially_zero=False,
                             optimization_level=3)
    metrics.update({
        "compiled_forward_depth": compiled.depth(),
        "compiled_forward_cx": compiled.count_ops().get("cx", 0),
        "classifier_complete": False,
        "oracle_exhaustively_verified": False,
    })
    print(json.dumps(metrics, indent=2))
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
