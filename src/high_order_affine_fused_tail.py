"""Depth-reduced residual-323 chain with a fused independent tail."""

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
CORRECTIONS = (
    (12, (2, 3, 4, 11)),
    (12, (7, 8, 10, 11)),
    (12, (2, 3, 11, 14)),
    (11, (8, 10, 12, 16)),
)


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
    circuit.append(RCCXGate(), [2, 3, 17])
    circuit.append(RCCXGate(), [7, 8, 13])
    circuit.append(RC3XGate(), [17, 4, 11, 12])
    circuit.append(RC3XGate(), [13, 10, 11, 12])
    circuit.append(RCCXGate(), [2, 3, 17])
    circuit.append(RCCXGate(), [7, 8, 13])

    # Independent partial products are computed before either dependent
    # target toggle. q12 must toggle before q11; both workspaces then clear.
    circuit.append(RCCXGate(), [2, 3, 17])
    circuit.append(RCCXGate(), [8, 10, 13])
    circuit.append(RC3XGate(), [17, 11, 14, 12])
    circuit.append(RC3XGate(), [13, 12, 16, 11])
    circuit.append(RCCXGate(), [2, 3, 17])
    circuit.append(RCCXGate(), [8, 10, 13])

    corrected = list(wires)
    for target, controls in CORRECTIONS:
        value = corrected[controls[0]]
        for control in controls[1:]:
            value &= corrected[control]
        corrected[target] ^= value
    if corrected[13] != 0 or corrected[17] != 0:
        raise AssertionError("clean ancillas were not restored")
    after, after_combo = exact_affine_distance(tuple(corrected))
    if after != 323:
        raise AssertionError(f"unexpected fused-tail residual: {after}")
    return circuit, {
        "experiment": "fused independent tail for residual-323 chain",
        "base_artifact": BASE.name,
        "base_affine_residual": before,
        "base_affine_combo": before_combo,
        "corrections": [[target, list(controls)] for target, controls in CORRECTIONS],
        "corrected_affine_residual": after,
        "corrected_affine_combo": after_combo,
        "semantic_inputs_checked": 4096,
        "clean_ancillas": [13, 17],
        "clean_ancillas_restored": True,
        "classifier_complete": False,
        "oracle_exhaustively_verified": False,
        "status": "best native-depth incomplete classifier candidate",
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
