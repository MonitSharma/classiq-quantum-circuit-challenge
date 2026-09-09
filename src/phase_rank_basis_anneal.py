"""Simulated-annealing search over rank bases scored by phase-cube depth."""

import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from factor import cubes_from_terms, synth
from qiskit import qasm2, transpile


def score(terms, seed):
    cubes = cubes_from_terms(terms)
    q = synth(cubes, seed=seed)
    out = transpile(q, basis_gates=["u3", "cx"],
                    qubits_initially_zero=False, optimization_level=3,
                    seed_transpiler=0)
    return (out.depth(), out.count_ops().get("cx", 0)), len(cubes), out


def search(steps=300, seed=20260910):
    rng = random.Random(seed)
    current = json.loads(Path("artifacts/rank_terms.json").read_text())
    current_score, current_cubes, _ = score(current, seed)
    best = None
    records = []
    for step in range(steps):
        i, j = rng.sample(range(10), 2)
        candidate = [list(term) for term in current]
        candidate[i][0] ^= candidate[j][0]
        candidate[j][1] ^= candidate[i][1] ^ candidate[j][1]
        # The previous line used the updated candidate[i]; restore the exact
        # elementary transformation with the original y_i value.
        # Rebuild from the pre-mutation values to avoid accidental drift.
        current_xi, current_yi = current[i]
        current_xj, current_yj = current[j]
        candidate = [list(term) for term in current]
        candidate[i] = [current_xi ^ current_xj, current_yi]
        candidate[j] = [current_xj, current_yj ^ current_yi]
        candidate_score, cube_count, out = score(candidate, step)
        temperature = max(1.0, 35.0 * (1.0 - step / steps))
        delta = candidate_score[0] - current_score[0]
        accept = delta <= 0 or rng.random() < math.exp(-delta / temperature)
        if accept:
            current, current_score = candidate, candidate_score
        row = {"step": step, "indices": (i, j), "score": candidate_score,
               "cube_count": cube_count, "accepted": accept}
        records.append(row)
        if best is None or candidate_score < best["score"]:
            best = {"score": candidate_score, "cube_count": cube_count,
                    "step": step, "indices": (i, j), "terms": candidate}
            Path("artifacts/phase_rank_basis_anneal_best_development.qasm").write_text(
                qasm2.dumps(out)
            )
            Path("artifacts/phase_rank_basis_anneal_best_development.metrics.json").write_text(
                json.dumps(best, indent=2)
            )
            print("best", best, flush=True)
        if step % 25 == 0:
            print("progress", step, current_score, flush=True)
    result = {"seed": seed, "steps": steps, "best": best, "records": records}
    Path("artifacts/phase_rank_basis_anneal_development.json").write_text(
        json.dumps(result, indent=2)
    )
    return best


if __name__ == "__main__":
    print(json.dumps(search(), indent=2))
