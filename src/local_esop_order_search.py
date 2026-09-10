"""Bounded local search over the exact 83-cube ESOP order.

This is a research helper: it keeps the v6 prefix, exact cover, and cleanup
fixed, and only changes the order in which phase cubes are emitted.
"""

from __future__ import annotations

import argparse
import json
import random
import warnings
from pathlib import Path

from qiskit import transpile

from high_order_affine_exact_esop_clean2_rel_ordered import (
    _append_cube,
    _ordered_terms,
)
from high_order_affine_exact_esop_clean2_rel_local import TERMS as LOCAL_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_local import TERMS as ORACLE_LOCAL_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves import TERMS as ORACLE_MOVES_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves2 import TERMS as ORACLE_MOVES2_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves3 import TERMS as ORACLE_MOVES3_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves4 import TERMS as ORACLE_MOVES4_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves5 import TERMS as ORACLE_MOVES5_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves6 import TERMS as ORACLE_MOVES6_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves7 import TERMS as ORACLE_MOVES7_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves8 import TERMS as ORACLE_MOVES8_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves9 import TERMS as ORACLE_MOVES9_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves10 import TERMS as ORACLE_MOVES10_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves11 import TERMS as ORACLE_MOVES11_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves12 import TERMS as ORACLE_MOVES12_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves13 import TERMS as ORACLE_MOVES13_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves14 import TERMS as ORACLE_MOVES14_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves15 import TERMS as ORACLE_MOVES15_TERMS
from high_order_affine_exact_esop_clean2_rel_oracle_moves16 import TERMS as ORACLE_MOVES16_TERMS
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


def score(circuit, complete_oracle=False):
    if complete_oracle:
        oracle = circuit.copy()
        oracle.z(12)
        oracle.compose(circuit.inverse(), inplace=True)
        circuit = oracle
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
    parser.add_argument("--start-local", action="store_true")
    parser.add_argument("--start-oracle-local", action="store_true")
    parser.add_argument("--start-oracle-moves", action="store_true")
    parser.add_argument("--start-oracle-moves2", action="store_true")
    parser.add_argument("--start-oracle-moves3", action="store_true")
    parser.add_argument("--start-oracle-moves4", action="store_true")
    parser.add_argument("--start-oracle-moves5", action="store_true")
    parser.add_argument("--start-oracle-moves6", action="store_true")
    parser.add_argument("--start-oracle-moves7", action="store_true")
    parser.add_argument("--start-oracle-moves8", action="store_true")
    parser.add_argument("--start-oracle-moves9", action="store_true")
    parser.add_argument("--start-oracle-moves10", action="store_true")
    parser.add_argument("--start-oracle-moves11", action="store_true")
    parser.add_argument("--start-oracle-moves12", action="store_true")
    parser.add_argument("--start-oracle-moves13", action="store_true")
    parser.add_argument("--start-oracle-moves14", action="store_true")
    parser.add_argument("--start-oracle-moves15", action="store_true")
    parser.add_argument("--start-oracle-moves16", action="store_true")
    parser.add_argument("--random-swaps", type=int, default=0)
    parser.add_argument("--complete-oracle", action="store_true")
    parser.add_argument("--random-seed", type=int, default=20260910)
    parser.add_argument("--random-moves", type=int, default=0)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if args.start_oracle_moves16:
            current = list(ORACLE_MOVES16_TERMS)
        elif args.start_oracle_moves15:
            current = list(ORACLE_MOVES15_TERMS)
        elif args.start_oracle_moves14:
            current = list(ORACLE_MOVES14_TERMS)
        elif args.start_oracle_moves13:
            current = list(ORACLE_MOVES13_TERMS)
        elif args.start_oracle_moves12:
            current = list(ORACLE_MOVES12_TERMS)
        elif args.start_oracle_moves11:
            current = list(ORACLE_MOVES11_TERMS)
        elif args.start_oracle_moves10:
            current = list(ORACLE_MOVES10_TERMS)
        elif args.start_oracle_moves9:
            current = list(ORACLE_MOVES9_TERMS)
        elif args.start_oracle_moves8:
            current = list(ORACLE_MOVES8_TERMS)
        elif args.start_oracle_moves7:
            current = list(ORACLE_MOVES7_TERMS)
        elif args.start_oracle_moves6:
            current = list(ORACLE_MOVES6_TERMS)
        elif args.start_oracle_moves5:
            current = list(ORACLE_MOVES5_TERMS)
        elif args.start_oracle_moves4:
            current = list(ORACLE_MOVES4_TERMS)
        elif args.start_oracle_moves3:
            current = list(ORACLE_MOVES3_TERMS)
        elif args.start_oracle_moves2:
            current = list(ORACLE_MOVES2_TERMS)
        elif args.start_oracle_moves:
            current = list(ORACLE_MOVES_TERMS)
        elif args.start_oracle_local:
            current = list(ORACLE_LOCAL_TERMS)
        else:
            current = list(LOCAL_TERMS if args.start_local else _ordered_terms())
        best_order = list(current)
        best_score = score(build_classifier_for_terms(best_order), args.complete_oracle)
        records = [{"kind": "baseline", "score": best_score}]
        for pass_index in range(args.passes):
            improved = False
            for index in range(len(best_order) - 1):
                trial = list(best_order)
                trial[index], trial[index + 1] = trial[index + 1], trial[index]
                trial_score = score(build_classifier_for_terms(trial), args.complete_oracle)
                records.append({"pass": pass_index, "index": index, "score": trial_score})
                if trial_score < best_score:
                    best_order, best_score = trial, trial_score
                    improved = True
                    print(json.dumps({"new_best": best_score, "index": index}))
            if not improved:
                break
        rng = random.Random(args.random_seed)
        for index in range(args.random_swaps):
            left, right = sorted(rng.sample(range(len(best_order)), 2))
            trial = list(best_order)
            trial[left], trial[right] = trial[right], trial[left]
            trial_score = score(build_classifier_for_terms(trial), args.complete_oracle)
            records.append({"kind": "random_swap", "left": left, "right": right, "score": trial_score})
            if trial_score < best_score:
                best_order, best_score = trial, trial_score
                print(json.dumps({"new_best": best_score, "left": left, "right": right}))
        for index in range(args.random_moves):
            left, right = sorted(rng.sample(range(len(best_order)), 2))
            trial = list(best_order)
            if rng.randrange(2) == 0:
                item = trial.pop(right)
                trial.insert(left, item)
                move = "insert"
            else:
                trial[left:right + 1] = reversed(trial[left:right + 1])
                move = "reverse"
            trial_score = score(build_classifier_for_terms(trial), args.complete_oracle)
            records.append({"kind": move, "left": left, "right": right, "score": trial_score})
            if trial_score < best_score:
                best_order, best_score = trial, trial_score
                print(json.dumps({"new_best": best_score, "move": move, "left": left, "right": right}))
        args.out.write_text(json.dumps({
            "best_forward_score": best_score,
            "order": [list(term) for term in best_order],
            "records": records,
        }, indent=2) + "\n")
        print(json.dumps({"best_forward_score": best_score, "tested": len(records)}))


if __name__ == "__main__":
    main()
