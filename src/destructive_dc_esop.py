"""Exact destructive classifier using a 15-wire reachable-state ESOP.

The residual after the v6 prefix is minimized with unreachable 15-wire states
as don't-cares by EXORCISM.  The frozen order below is the result of a bounded
complete-oracle insertion/reversal search.  The v6 prefix and two-clean
relative-phase lowering are otherwise unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from qiskit import qasm2, transpile

from destructive_semantic_search import TARGET
from high_order_affine_exact_esop import CHART, _replay
from high_order_affine_exact_esop_clean2_rel import (
    _append_cube,
    _clear_q13,
    _clear_q17,
    _restore_q17,
)
from high_order_affine_no_uncompute_v6 import build_candidate_v6


# 53-cube ESOP from the 15-input reachable-state don't-care screen, reordered
# by deterministic insertion/reversal searches against the complete C-dagger-Z-C
# oracle.  Each pair is (positive_literal_mask, negative_literal_mask) over
# CHART = (q0..q11,q14,q15,q16).
TERMS = (
    (23341, 9296), (26146, 6420), (1856, 26790), (5952, 26814),
    (16864, 11798), (4576, 11798), (808, 31766), (13864, 18710),
    (744, 32022), (23024, 9742), (2296, 30214), (2524, 30240),
    (1884, 30880), (3996, 28704), (2588, 29984), (21226, 11541),
    (2482, 29773), (2354, 30285), (2523, 30244), (1883, 30884),
    (2364, 29827), (2364, 30275), (26276, 6483), (22772, 9995),
    (9264, 23311), (9248, 23503), (23469, 9298), (993, 31774),
    (26277, 6490), (23102, 9472), (21222, 11544), (23330, 9428),
    (3058, 29700), (4576, 28176), (26148, 6544), (1856, 30880),
    (22772, 9992), (26274, 6424), (23338, 9424), (2552, 30210),
    (21304, 11270), (22832, 9742), (26347, 6420), (26159, 6544),
    (3483, 21028), (3483, 28708), (2843, 29732), (2075, 29220),
    (3099, 21028), (23343, 9360), (32160, 543), (30000, 2703),
    (3060, 29707),
)


def build_classifier():
    circuit, metrics = build_candidate_v6()
    base_wires = _replay(circuit)
    _clear_q13(circuit)
    _clear_q17(circuit)
    for positive, negative in TERMS:
        _append_cube(circuit, positive, negative)
    _restore_q17(circuit)
    _clear_q13(circuit)
    circuit.cx(11, 12)
    wires = _replay(circuit)
    if wires[12] != TARGET or wires[13] != base_wires[13] or wires[17] != base_wires[17]:
        raise AssertionError("don't-care ESOP classifier replay failed")
    metrics = dict(metrics)
    metrics.update({
        "experiment": "15-wire reachable-state don't-care ESOP",
        "esop_terms": len(TERMS),
        "esop_literals": sum(p.bit_count() + n.bit_count() for p, n in TERMS),
        "esop_chart_wires": list(CHART),
        "esop_order": "200-move continuation from the prior frozen order",
        "target_wire": 12,
        "semantic_inputs_checked": 4096,
        "classifier_complete": True,
        "oracle_exhaustively_verified": False,
    })
    return circuit, metrics


def build_oracle():
    classifier, metrics = build_classifier()
    oracle = classifier.copy()
    oracle.z(12)
    oracle.compose(classifier.inverse(), inplace=True)
    return oracle, metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-oracle-qasm", type=Path, required=True)
    parser.add_argument("--out-metrics", type=Path, required=True)
    args = parser.parse_args()
    classifier, metrics = build_classifier()
    compiled = transpile(
        classifier, basis_gates=["u3", "cx"], qubits_initially_zero=False,
        optimization_level=3, seed_transpiler=0,
    )
    oracle, _ = build_oracle()
    oracle_compiled = transpile(
        oracle, basis_gates=["u3", "cx"], qubits_initially_zero=False,
        optimization_level=3, seed_transpiler=0,
    )
    args.out_oracle_qasm.parent.mkdir(parents=True, exist_ok=True)
    args.out_oracle_qasm.write_text(qasm2.dumps(oracle_compiled))
    metrics.update({
        "compiled_forward_depth": compiled.depth(),
        "compiled_forward_cx": compiled.count_ops().get("cx", 0),
        "oracle_depth": oracle_compiled.depth(),
        "oracle_cx": oracle_compiled.count_ops().get("cx", 0),
        "oracle_qasm_sha256": hashlib.sha256(args.out_oracle_qasm.read_bytes()).hexdigest(),
        "transpilation": {
            "basis_gates": ["u3", "cx"],
            "qubits_initially_zero": False,
            "optimization_level": 3,
            "seed_transpiler": 0,
        },
    })
    args.out_metrics.parent.mkdir(parents=True, exist_ok=True)
    args.out_metrics.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
