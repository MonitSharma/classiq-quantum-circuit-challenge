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


def compile_blocks(blocks, order):
    q = QuantumCircuit(18)
    for i in order: q.compose(blocks[i], inplace=True)
    return transpile(q, basis_gates=["u3", "cx"], optimization_level=3,
                     qubits_initially_zero=False)


def metric(q):
    return {"depth": q.depth(), "cx": q.count_ops().get("cx", 0), "width": q.num_qubits}


def pair_blocks(terms):
    return [pair_circuit(x, y) for x, y in terms]


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

    # Use only already-generated, basis-matched portfolio blocks for the
    # substitution closure.  This keeps the search exact and avoids pretending
    # that incompatible retention schedules are reusable across bases.
    pareto = "rank_mc_pareto_terms"
    choices = [[("pair_circuit", block)] for block in all_blocks[pareto]]
    for i in range(10):
        for path in sorted((root / "rank_portfolio_blocks").glob(f"term_{i}_*.qasm")):
            compiler = path.stem.split(f"term_{i}_", 1)[1]
            if compiler != "pair_circuit":
                choices[i].append((compiler, QuantumCircuit.from_qasm_file(str(path))))
    base = compile_blocks([c[0][1] for c in choices], list(range(10)))
    base_score = metric(base)
    one = []; two = []
    for i in range(10):
        for alt, block in choices[i][1:]:
            blocks = [choices[k][0][1] for k in range(10)]
            blocks[i] = block
            out = compile_blocks(blocks, range(10))
            one.append({"basis": pareto, "changed_terms": [i], "assignment": [choices[k][0][0] if k != i else alt for k in range(10)], **metric(out),
                        "delta_depth": out.depth() - base_score["depth"], "delta_cx": out.count_ops().get("cx", 0) - base_score["cx"]})
    for i in range(10):
        for j in range(i + 1, 10):
            for alt_i, block_i in choices[i][1:]:
                for alt_j, block_j in choices[j][1:]:
                    blocks = [choices[k][0][1] for k in range(10)]
                    blocks[i], blocks[j] = block_i, block_j
                    out = compile_blocks(blocks, range(10))
                    assignment = [choices[k][0][0] for k in range(10)]
                    assignment[i], assignment[j] = alt_i, alt_j
                    two.append({"basis": pareto, "changed_terms": [i, j], "assignment": assignment, **metric(out),
                                "delta_depth": out.depth() - base_score["depth"], "delta_cx": out.count_ops().get("cx", 0) - base_score["cx"]})
    payload = {"baseline": base_score, "choices": [[x[0] for x in c] for c in choices],
               "one_substitutions": sorted(one, key=lambda r: (r["depth"], r["cx"])),
               "two_substitutions": sorted(two, key=lambda r: (r["depth"], r["cx"]))}
    (root / "anchored_one_substitution.json").write_text(json.dumps(payload["one_substitutions"], indent=2))
    (root / "anchored_two_substitution.json").write_text(json.dumps(payload["two_substitutions"], indent=2))
    (root / "anchored_rank_search_summary.json").write_text(json.dumps({
        "baselines": baselines, "pareto_choices": payload["choices"],
        "best_one": payload["one_substitutions"][:10], "best_two": payload["two_substitutions"][:20]
    }, indent=2))
    print(json.dumps({"baselines": baselines, "pareto_base": base_score,
                      "one_count": len(one), "two_count": len(two),
                      "best_one": payload["one_substitutions"][:3],
                      "best_two": payload["two_substitutions"][:3]}, indent=2))


if __name__ == "__main__": main()
