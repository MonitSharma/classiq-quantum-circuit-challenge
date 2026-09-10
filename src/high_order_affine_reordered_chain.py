"""Reordered four-control continuation from the best clean-ancilla basin.

The fourth-control correction on q12 is intentionally placed before the
q11 correction.  The semantic order matters: the same two products give a
residual of 323 in this order, while appending the q12 correction after the
q11 correction worsens the residual.
"""

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
    # This q12 correction must precede the q11 correction.
    (12, (2, 3, 11, 14)),
    (11, (5, 8, 10, 12)),
)


def append_clean_mcx4(circuit, target: int, controls: tuple[int, ...], clean: int):
    if len(controls) != 4 or clean in controls or clean == target:
        raise ValueError("expected four controls disjoint from the clean workspace")
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

    # The first two products use separate clean workspaces and can be
    # scheduled in parallel by the transpiler.
    append_clean_mcx4(circuit, 12, (2, 3, 4, 11), 17)
    append_clean_mcx4(circuit, 12, (7, 8, 10, 11), 13)
    # Reordered continuation: q12 ^= q2&q3&q11&q14, then q11 ^= q5&q8&q10&q12.
    append_clean_mcx4(circuit, 12, (2, 3, 11, 14), 17)
    append_clean_mcx4(circuit, 11, (5, 8, 10, 12), 17)

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
        raise AssertionError(f"unexpected reordered-chain residual: {after}")
    return circuit, {
        "experiment": "reordered four-control continuation",
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
