"""No-uncompute destructive classifier candidate.

The forward classifier deliberately leaves two partial products in q13 and
q17.  This is legal for C: only the selected midpoint bit is constrained;
the exact inverse used by the phase oracle would restore all wires later.
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
SIGNED = ((5, False), (7, True), (8, True), (9, False), (15, True))


def signed_value(wires, controls):
    mask = (1 << 4096) - 1
    value = mask
    for wire, positive in controls:
        value &= wires[wire] if positive else mask ^ wires[wire]
    return value


def build_candidate(base_path: Path = BASE):
    record = json.loads(base_path.read_text())
    gates = tuple(tuple(gate) for gate in record["gates"])
    wires = list(initial_wire_truth_tables())
    for _, a, b, target in gates:
        wires = list(apply_rccx_semantic(tuple(wires), a, b, target))
    before, before_combo = exact_affine_distance(tuple(wires))
    circuit = build_circuit(gates)

    # Signed five-control correction, retaining its q2? no: q17 partial.
    for wire, positive in SIGNED:
        if not positive:
            circuit.x(wire)
    circuit.append(RC3XGate(), [5, 7, 8, 17])
    circuit.append(RC3XGate(), [17, 9, 15, 11])
    for wire, positive in reversed(SIGNED):
        if not positive:
            circuit.x(wire)
    corrected = list(wires)
    corrected[11] ^= signed_value(corrected, SIGNED)
    # The retained partial includes the negative q5 control; q17 is garbage,
    # but it must still describe the actual circuit state.
    mask = (1 << 4096) - 1
    corrected[17] = (mask ^ corrected[5]) & corrected[7] & corrected[8]
    # Positive four-control correction, retaining q2&q3 in q13.
    circuit.append(RCCXGate(), [2, 3, 13])
    circuit.append(RC3XGate(), [13, 4, 11, 12])
    corrected[12] ^= corrected[2] & corrected[3] & corrected[4] & corrected[11]
    corrected[13] = corrected[2] & corrected[3]
    after, after_combo = exact_affine_distance(tuple(corrected))
    if after != 331:
        raise AssertionError(f"unexpected no-uncompute residual: {after}")
    if corrected[13] == 0 or corrected[17] == 0:
        raise AssertionError("retained garbage partial products unexpectedly vanished")
    return circuit, {
        "experiment": "no-uncompute destructive forward classifier",
        "base_artifact": BASE.name,
        "base_affine_residual": before,
        "base_affine_combo": before_combo,
        "corrections": [
            [11, [[wire, positive] for wire, positive in SIGNED]],
            [12, [2, 3, 4, 11]],
        ],
        "corrected_affine_residual": after,
        "corrected_affine_combo": after_combo,
        "semantic_inputs_checked": 4096,
        "midpoint_garbage_wires": [13, 17],
        "midpoint_garbage_nonzero": True,
        "classifier_complete": False,
        "oracle_exhaustively_verified": False,
        "status": "best no-uncompute depth candidate; incomplete classifier",
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
