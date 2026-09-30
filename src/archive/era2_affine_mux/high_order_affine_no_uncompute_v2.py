"""No-uncompute candidate with one direct retained-garbage correction."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from qiskit import transpile
from qiskit.circuit.library import RC3XGate

from destructive_semantic_search import (
    apply_rccx_semantic,
    exact_affine_distance,
    initial_wire_truth_tables,
)
from high_order_affine_no_uncompute import build_candidate


BASE = Path(__file__).resolve().parents[1] / "artifacts" / "destructive_semantic" / (
    "double_seed42_b16x6_p4_depth59.json"
)


def semantic_state():
    record = json.loads(BASE.read_text())
    wires = list(initial_wire_truth_tables())
    for _, a, b, target in record["gates"]:
        wires = list(apply_rccx_semantic(tuple(wires), a, b, target))
    mask = (1 << 4096) - 1
    signed = ((5, False), (7, True), (8, True), (9, False), (15, True))
    value = mask
    for wire, positive in signed:
        value &= wires[wire] if positive else mask ^ wires[wire]
    wires[11] ^= value
    value = wires[2] & wires[3]
    wires[13] = value
    wires[17] = (mask ^ wires[5]) & wires[7] & wires[8]
    wires[12] ^= wires[2] & wires[3] & wires[4] & wires[11]
    wires[12] ^= wires[11] & wires[13] & wires[14]
    return wires


def build_candidate_v2():
    circuit, metrics = build_candidate()
    circuit.append(RC3XGate(), [11, 13, 14, 12])
    wires = semantic_state()
    residual, combo = exact_affine_distance(tuple(wires))
    if residual != 315 or wires[13] == 0 or wires[17] == 0:
        raise AssertionError("unexpected no-uncompute v2 semantics")
    metrics = dict(metrics)
    metrics.update({
        "experiment": "no-uncompute destructive classifier v2",
        "additional_correction": [12, [11, 13, 14]],
        "corrected_affine_residual": residual,
        "corrected_affine_combo": combo,
        "status": "best no-uncompute depth/residual Pareto candidate; incomplete classifier",
    })
    return circuit, metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        circuit, metrics = build_candidate_v2()
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
