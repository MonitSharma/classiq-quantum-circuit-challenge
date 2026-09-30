"""Bounded rank-basis search scored by complete serialized circuit depth."""

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
    return transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False, optimization_level=3)


def search(steps=60, seed=20260908):
    rng = random.Random(seed)
    current = json.loads(Path('artifacts/pair_terms.json').read_text())
    current_q = compile_full(current)
    current_score = (current_q.depth(), current_q.count_ops().get('cx', 0))
    best = (current_score, current.copy(), current_q)
    for step in range(steps):
        i, j = rng.sample(range(len(current)), 2)
        xi, yi = current[i]
        xj, yj = current[j]
        candidate = current.copy()
        candidate[i] = [xi ^ xj, yi]
        candidate[j] = [xj, yi ^ yj]
        try:
            q = compile_full(candidate)
        except ValueError:
            print('skip', step, 'uncompilable pair', flush=True)
            continue
        score = (q.depth(), q.count_ops().get('cx', 0))
        temperature = max(1.0, 30.0 * (1.0 - step / max(1, steps)))
        delta = score[0] - current_score[0]
        accept = delta <= 0 or rng.random() < math.exp(-delta / temperature)
        if accept:
            current, current_q, current_score = candidate, q, score
        if score < best[0]:
            best = (score, candidate.copy(), q)
            print('best', step, score, flush=True)
            Path('artifacts/actual_pair_basis_best.qasm').write_text(qasm2.dumps(q))
            Path('artifacts/actual_pair_basis_best.json').write_text(json.dumps({'step': step, 'seed': seed, 'score': score, 'terms': candidate}, indent=2))
        elif step % 5 == 0:
            print('progress', step, 'score', score, 'current', current_score, flush=True)
    return best


if __name__ == '__main__':
    best = search()
    print('final', best[0], flush=True)
