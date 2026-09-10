"""Bounded local search over the exact 83-cube ESOP order.

This is a research helper: it keeps the v6 prefix, exact cover, and cleanup
fixed, and only changes the order in which phase cubes are emitted.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from qiskit import transpile

from high_order_affine_exact_esop_clean2_rel_ordered import (
    _append_cube,
    _ordered_terms,
)
from high_order_affine_exact_esop_clean2_rel import (
    _clear_q13,
    _clear_q17,
    _restore_q17,
)
from high_order_affine_exact_esop_clean1 import _replay
from high_order_affine_no_uncompute_v6 import build_candidate_v6


def build_classifier_for_terms(terms):
    circuit, _ = build_candidate_v6()
    base_wires = _replay(circuit)
    _clear_q13(circuit)
    _clear_q17(circuit)
    for positive, negative in terms:
        _append_cube(circuit, positive, negative)
    _restore_q17(circuit)
    _clear_q13(circuit)
    circuit.cx(11, 12)
    wires = _replay(circuit)
    if wires[13] != base_wires[13] or wires[17] != base_wires[17]:
        raise AssertionError("cleanup changed v6 ancilla semantics")
    return circuit


def score(circuit):
    compiled = transpile(
        circuit,
        basis_gates=["u3", "cx"],
        qubits_initially_zero=False,
        optimization_level=3,
        seed_transpiler=0,
    )
    return compiled.depth(), compiled.count_ops().get("cx", 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--passes", type=int, default=1)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        current = list(_ordered_terms())
        best_order = list(current)
        best_score = score(build_classifier_for_terms(best_order))
        records = [{"kind": "baseline", "score": best_score}]
        for pass_index in range(args.passes):
            improved = False
            for index in range(len(best_order) - 1):
                trial = list(best_order)
                trial[index], trial[index + 1] = trial[index + 1], trial[index]
                trial_score = score(build_classifier_for_terms(trial))
                records.append({"pass": pass_index, "index": index, "score": trial_score})
                if trial_score < best_score:
                    best_order, best_score = trial, trial_score
                    improved = True
                    print(json.dumps({"new_best": best_score, "index": index}))
            if not improved:
                break
        args.out.write_text(json.dumps({
            "best_forward_score": best_score,
            "order": [list(term) for term in best_order],
            "records": records,
        }, indent=2) + "\n")
        print(json.dumps({"best_forward_score": best_score, "tested": len(records)}))


if __name__ == "__main__":
    main()
