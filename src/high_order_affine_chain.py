"""Build the best depth-screened clean-ancilla correction chain."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import RCCXGate, RC3XGate

from destructive_semantic_search import (
    TARGET,
    apply_rccx_semantic,
    build_circuit,
    exact_affine_distance,
    initial_wire_truth_tables,
)


BASE = Path(__file__).resolve().parents[1] / "artifacts" / "destructive_semantic" / (
    "double_seed42_b16x6_p4_depth59.json"
)
CORRECTIONS = (
    (12, (2, 3, 4, 8, 11)),
    (12, (7, 8, 10, 11)),
    (11, (5, 8, 10, 12)),
)


def append_clean_mcx(circuit: QuantumCircuit, target: int,
                     controls: tuple[int, ...], clean: int = 17) -> None:
    if clean in controls or clean == target:
        raise ValueError("clean workspace must be disjoint from the correction")
    if len(controls) == 5:
        a, b, c, d, e = controls
        circuit.append(RC3XGate(), [a, b, c, clean])
        circuit.append(RC3XGate(), [clean, d, e, target])
        circuit.append(RC3XGate(), [a, b, c, clean])
    elif len(controls) == 4:
        a, b, c, d = controls
        circuit.append(RCCXGate(), [a, b, clean])
        circuit.append(RC3XGate(), [clean, c, d, target])
        circuit.append(RCCXGate(), [a, b, clean])
    else:
        raise ValueError("this chain only uses four- and five-control blocks")


def build_chain(base_path: Path = BASE):
    record = json.loads(base_path.read_text())
    gates = tuple(tuple(gate) for gate in record["gates"])
    wires = initial_wire_truth_tables()
    for _, a, b, target in gates:
        wires = apply_rccx_semantic(wires, a, b, target)
    if wires[17] != 0:
        raise AssertionError("q17 is not clean before the chain")
    before, before_combo = exact_affine_distance(wires)

    circuit = build_circuit(gates)
    corrected = list(wires)
    for target, controls in CORRECTIONS:
        append_clean_mcx(circuit, target, controls)
        value = corrected[controls[0]]
        for control in controls[1:]:
            value &= corrected[control]
        corrected[target] ^= value
        if corrected[17] != 0:
            raise AssertionError("q17 was not restored after a correction")
    after, after_combo = exact_affine_distance(tuple(corrected))
    if after != 339:
        raise AssertionError(f"unexpected chain residual: {after}")
    return circuit, {
        "base_affine_residual": before,
        "base_affine_combo": before_combo,
        "corrections": [[target, list(controls)] for target, controls in CORRECTIONS],
        "corrected_affine_residual": after,
        "corrected_affine_combo": after_combo,
        "semantic_inputs_checked": 4096,
        "clean_ancilla": 17,
        "clean_ancilla_restored": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        circuit, metrics = build_chain()
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
