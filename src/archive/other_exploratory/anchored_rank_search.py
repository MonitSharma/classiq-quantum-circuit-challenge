"""Bounded, reproducible scalar closure search anchored on pair_circuit.

The historical portfolio alternatives are available for the Pareto basis.  For
the other bases this driver still records authoritative all-pair baselines;
it never silently substitutes a block from a different basis.
"""

import hashlib
import json
import random
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from pair_search import pair_circuit
from parallel_rank_pair_xag import parallel_pair
from phase_pebble_rank import compile_pair as compile_phase_pebble
from minmc_rank_pair import compile_side


def compile_blocks(blocks, order):
    q = QuantumCircuit(18)
    for i in order: q.compose(blocks[i], inplace=True)
    return transpile(q, basis_gates=["u3", "cx"], optimization_level=3,
                     qubits_initially_zero=False)


def metric(q):
    return {"depth": q.depth(), "cx": q.count_ops().get("cx", 0), "width": q.num_qubits}


def pair_blocks(terms):
    return [pair_circuit(x, y) for x, y in terms]


def portfolio_choices(terms):
    cache = json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    choices = []
    for x, y in terms:
        row = [("pair_circuit", pair_circuit(x, y))]
        try: row.append(("parallel_rank_pair_xag", parallel_pair(x, y)[3]))
        except Exception: pass
        try:
            cx = compile_side(cache[str(x)], list(range(6)), 12, [13, 14])
            cy = compile_side(cache[str(y)], list(range(6, 12)), 15, [16, 17])
            pre = QuantumCircuit(18); pre.compose(cx, inplace=True); pre.compose(cy, inplace=True)
            block = pre.copy(); block.cz(12, 15); block.compose(pre.inverse(), inplace=True)
            row.append(("minmc_rank_pair", block))
        except Exception: pass
        try: row.append(("phase_pebble", compile_phase_pebble(x, y, cache)[0]))
        except Exception: pass
        choices.append(row)
    return choices


def main():
    root = Path("artifacts")
    basis_names = ["pair_terms", "rank_terms", "rank_mc_pareto_terms"]
    baselines = {}; all_blocks = {}
    for name in basis_names:
        terms = json.loads((root / f"{name}.json").read_text())
        blocks = pair_blocks(terms)
        out = compile_blocks(blocks, list(range(10)))
        baselines[name] = {**metric(out), "assignment": ["pair_circuit"] * 10}
        all_blocks[name] = blocks
    (root / "anchored_rank_baselines.json").write_text(json.dumps(baselines, indent=2))

    all_search = {}
    for basis in basis_names:
        terms = json.loads((root / f"{basis}.json").read_text())
        choices = portfolio_choices(terms)
        base_score = metric(compile_blocks([c[0][1] for c in choices], range(10)))
        one = []; two = []
        for i in range(10):
            for alt, block in choices[i][1:]:
                blocks = [choices[k][0][1] for k in range(10)]; blocks[i] = block
                out = compile_blocks(blocks, range(10))
                one.append({"basis": basis, "changed_terms": [i], "assignment": [alt if k == i else "pair_circuit" for k in range(10)], **metric(out),
                            "delta_depth": out.depth() - base_score["depth"], "delta_cx": out.count_ops().get("cx", 0) - base_score["cx"]})
        for i in range(10):
            for j in range(i + 1, 10):
                for alt_i, block_i in choices[i][1:]:
                    for alt_j, block_j in choices[j][1:]:
                        blocks = [choices[k][0][1] for k in range(10)]; blocks[i], blocks[j] = block_i, block_j
                        out = compile_blocks(blocks, range(10)); assignment = ["pair_circuit"] * 10
                        assignment[i], assignment[j] = alt_i, alt_j
                        two.append({"basis": basis, "changed_terms": [i, j], "assignment": assignment, **metric(out),
                                    "delta_depth": out.depth() - base_score["depth"], "delta_cx": out.count_ops().get("cx", 0) - base_score["cx"]})
        all_search[basis] = {"baseline": base_score, "choices": [[x[0] for x in c] for c in choices],
                             "one": sorted(one, key=lambda r: (r["depth"], r["cx"])),
                             "two": sorted(two, key=lambda r: (r["depth"], r["cx"]))}
    (root / "anchored_one_substitution.json").write_text(json.dumps({k: v["one"] for k, v in all_search.items()}, indent=2))
    (root / "anchored_two_substitution.json").write_text(json.dumps({k: v["two"] for k, v in all_search.items()}, indent=2))
    (root / "anchored_rank_search_summary.json").write_text(json.dumps({"baselines": baselines, "search": all_search}, indent=2))
    print(json.dumps({"baselines": baselines, "search": {k: {"one_count": len(v["one"]), "two_count": len(v["two"]),
                      "best_one": v["one"][:1], "best_two": v["two"][:1]} for k, v in all_search.items()}}, indent=2))


if __name__ == "__main__": main()
