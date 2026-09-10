"""Search equivalent rank bases using complete direct phase-cube depth."""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from factor import cubes_from_terms, synth
from qiskit import qasm2, transpile


def compile_terms(terms, seed):
    cubes = cubes_from_terms(terms)
    q = synth(cubes, seed=seed)
    out = transpile(q, basis_gates=["u3", "cx"],
                    qubits_initially_zero=False, optimization_level=3,
                    seed_transpiler=0)
    return out, len(cubes)


def search(steps=100, seed=20260909):
    rng = random.Random(seed)
    current = json.loads(Path("artifacts/rank_terms.json").read_text())
    best = None
    records = []
    for step in range(steps):
        i, j = rng.sample(range(10), 2)
        xi, yi = current[i]
        xj, yj = current[j]
        candidate = [list(term) for term in current]
        candidate[i] = [xi ^ xj, yi]
        candidate[j] = [xj, yi ^ yj]
        out, cube_count = compile_terms(candidate, step)
        score = (out.depth(), out.count_ops().get("cx", 0))
        row = {"step": step, "indices": (i, j), "score": score,
               "cube_count": cube_count}
        records.append(row)
        # Greedy descent on the actual complete serialized circuit.
        if best is None or score < best["score"]:
            best = {"score": score, "cube_count": cube_count,
                    "step": step, "indices": (i, j), "terms": candidate}
            Path("artifacts/phase_rank_basis_best_development.qasm").write_text(
                qasm2.dumps(out)
            )
            Path("artifacts/phase_rank_basis_best_development.metrics.json").write_text(
                json.dumps(best, indent=2)
            )
            print("best", best, flush=True)
            current = candidate
    result = {"seed": seed, "steps": steps, "best": best, "records": records}
    Path("artifacts/phase_rank_basis_search_development.json").write_text(
        json.dumps(result, indent=2)
    )
    return best


if __name__ == "__main__":
    print(json.dumps(search(), indent=2))
