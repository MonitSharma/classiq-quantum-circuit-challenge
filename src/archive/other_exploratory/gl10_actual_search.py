"""Bounded GL(10,2) rank-basis search scored by serialized circuit cost."""

import json
import math
import random
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

from pair_search import pair_circuit


def compile_full(terms):
    q = QuantumCircuit(18)
    for x, y in terms:
        q.compose(pair_circuit(x, y), inplace=True)
    return transpile(q, basis_gates=["u3", "cx"],
                     qubits_initially_zero=False, optimization_level=3)


def score(q):
    return q.depth(), q.count_ops().get("cx", 0)


def run(start_name, start_terms, steps=80, seed=20260909):
    rng = random.Random(seed)
    current = [list(pair) for pair in start_terms]
    current_q = compile_full(current)
    current_score = score(current_q)
    best = (current_score, current, current_q)
    print(start_name, "initial", current_score, flush=True)
    for step in range(steps):
        i, j = rng.sample(range(10), 2)
        xi, yi = current[i]
        xj, yj = current[j]
        candidate = [pair[:] for pair in current]
        # Elementary transvection on U and the inverse-transpose action on V.
        candidate[i] = [xi ^ xj, yi]
        candidate[j] = [xj, yi ^ yj]
        try:
            q = compile_full(candidate)
        except ValueError:
            continue
        candidate_score = score(q)
        delta = candidate_score[0] - current_score[0]
        temperature = max(1.0, 25.0 * (1.0 - step / max(1, steps)))
        if delta <= 0 or rng.random() < math.exp(-delta / temperature):
            current, current_q, current_score = candidate, q, candidate_score
        if candidate_score < best[0]:
            best = (candidate_score, [pair[:] for pair in candidate], q)
            print(start_name, "best", step, candidate_score, flush=True)
    return best


def main():
    starts = {}
    for name in ("pair_terms", "rank_terms", "rank_mc_pareto_terms"):
        starts[name] = json.loads(Path(f"artifacts/{name}.json").read_text())
    overall = None
    report = {}
    for index, (name, terms) in enumerate(starts.items()):
        result = run(name, terms, seed=20260909 + index)
        report[name] = {"score": result[0], "terms": result[1], "steps": 80}
        if overall is None or result[0] < overall[0]:
            overall = result
    Path("artifacts/gl10_actual_search.json").write_text(json.dumps(report, indent=2))
    if overall and overall[0][0] < 779:
        Path("artifacts/gl10_actual_best.qasm").write_text(qasm2.dumps(overall[2]))
    print(json.dumps({name: value["score"] for name, value in report.items()}, indent=2))


if __name__ == "__main__":
    main()
