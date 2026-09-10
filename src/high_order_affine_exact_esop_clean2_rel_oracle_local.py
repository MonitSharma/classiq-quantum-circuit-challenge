"""Frozen full-oracle local-search ordering for the exact 83-cube ESOP.

The v6 prefix, exact cover, cleanup, and relative-phase lowering are unchanged.
This order was selected by deterministic random single-swap search scored on the
complete serialized C-dagger-Z-C oracle.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

from qiskit import qasm2, transpile

import high_order_affine_exact_esop_clean2_rel_ordered as _base

TERMS = ((740, 20491), (2786, 20493), (2722, 16397), (738, 20484), (744, 20496), (1000, 20496), (1001, 20496), (993, 20496), (18631, 520), (24576, 4499), (2940, 16515), (2172, 16515), (2284, 22019), (172, 22019), (2280, 17922), (24580, 4440), (1856, 12453), (24584, 4501), (24584, 4373), (24576, 4501), (2856, 16515), (24576, 4497), (24576, 4498), (24576, 4500), (24584, 4564), (24584, 4436), (24584, 4565), (24584, 4437), (24576, 4563), (24576, 4435), (24580, 4443), (24580, 4571), (4576, 17936), (24580, 4570), (25094, 4440), (25094, 280), (26752, 9), (25094, 4505), (8336, 4111), (8432, 20751), (8304, 20745), (8192, 6873), (808, 20496), (18629, 520), (18630, 520), (21190, 2056), (21448, 2053), (21192, 2053), (21256, 2048), (1864, 10288), (12328, 16656), (1864, 14517), (1856, 28845), (1856, 28808), (5968, 10272), (3100, 8192), (16576, 4614), (2590, 16640), (2590, 256), (18974, 448), (18958, 192), (18959, 64), (18959, 128), (18975, 384), (18975, 320), (19215, 192), (18701, 192), (18688, 8776), (18688, 8396), (18688, 8840), (22800, 8841), (20752, 649), (18736, 8909), (2352, 717), (2329, 4836), (2073, 4708), (2073, 4964), (2073, 4900), (2329, 4260), (2841, 4260), (2841, 4132), (2588, 16640), (2508, 4640),)


def build_classifier():
    original = _base._ordered_terms
    _base._ordered_terms = lambda: TERMS
    try:
        circuit, metrics = _base.build_classifier()
    finally:
        _base._ordered_terms = original
    metrics = dict(metrics)
    metrics.update({
        "experiment": "exact ESOP complete-oracle random-swap order",
        "esop_order": "deterministic random single-swap search scored complete oracle",
        "local_search_random_seed": 20260910,
        "local_search_random_swaps": 60,
    })
    return circuit, metrics


def build_oracle():
    classifier, metrics = build_classifier()
    oracle = classifier.copy()
    oracle.z(12)
    oracle.compose(classifier.inverse(), inplace=True)
    return oracle, metrics


def main():
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--out-oracle-qasm", type=Path)
    parser.add_argument("--out-metrics", type=Path)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        classifier, metrics = build_classifier()
        compiled = transpile(classifier, basis_gates=["u3", "cx"],
                             qubits_initially_zero=False, optimization_level=3,
                             seed_transpiler=0)
        oracle, _ = build_oracle()
        oracle_compiled = transpile(oracle, basis_gates=["u3", "cx"],
                                    qubits_initially_zero=False, optimization_level=3,
                                    seed_transpiler=0)
    metrics.update({
        "compiled_forward_depth": compiled.depth(),
        "compiled_forward_cx": compiled.count_ops().get("cx", 0),
        "oracle_depth": oracle_compiled.depth(),
        "oracle_cx": oracle_compiled.count_ops().get("cx", 0),
        "transpilation": {"basis_gates": ["u3", "cx"],
                           "qubits_initially_zero": False,
                           "optimization_level": 3, "seed_transpiler": 0},
    })
    if args.out_oracle_qasm is not None:
        args.out_oracle_qasm.parent.mkdir(parents=True, exist_ok=True)
        args.out_oracle_qasm.write_text(qasm2.dumps(oracle_compiled))
        metrics["oracle_qasm_sha256"] = hashlib.sha256(args.out_oracle_qasm.read_bytes()).hexdigest()
    if args.out_metrics is not None:
        args.out_metrics.parent.mkdir(parents=True, exist_ok=True)
        args.out_metrics.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
