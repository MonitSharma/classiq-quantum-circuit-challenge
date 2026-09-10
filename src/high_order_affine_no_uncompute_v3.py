"""No-uncompute v3: correct the dominant residual with a restored partial."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from qiskit import transpile
from qiskit.circuit.library import RCCXGate, RC3XGate

from destructive_semantic_search import apply_rccx_semantic, exact_affine_distance, initial_wire_truth_tables
from high_order_affine_no_uncompute_v2 import BASE, build_candidate_v2, semantic_state


def build_candidate_v3():
    circuit, metrics = build_candidate_v2()

    # q17 retains (not computes-and-uncomputes) the signed partial from v2.
    # q14 is used as a temporary partial and restored, so this is an exact
    # four-control correction despite the intentionally dirty midpoint state.
    circuit.x(15)
    circuit.append(RCCXGate(), [9, 10, 14])
    circuit.append(RC3XGate(), [14, 15, 17, 11])
    circuit.append(RCCXGate(), [9, 10, 14])
    circuit.x(15)

    wires = list(semantic_state())
    mask = (1 << 4096) - 1
    wires[15] ^= mask
    wires[14] ^= wires[9] & wires[10]
    wires[11] ^= wires[14] & wires[15] & wires[17]
    wires[14] ^= wires[9] & wires[10]
    wires[15] ^= mask
    residual, combo = exact_affine_distance(tuple(wires))
    if residual != 279 or wires[13] == 0 or wires[17] == 0:
        raise AssertionError("unexpected no-uncompute v3 semantics")

    metrics = dict(metrics)
    metrics.update({
        "experiment": "no-uncompute destructive classifier v3",
        "additional_correction": [
            11,
            [9, 10, [15, False], 17],
        ],
        "corrected_affine_residual": residual,
        "corrected_affine_combo": combo,
        "midpoint_garbage_wires": [13, 17],
        "status": "best no-uncompute depth/residual Pareto candidate; incomplete classifier",
    })
    return circuit, metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        circuit, metrics = build_candidate_v3()
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
