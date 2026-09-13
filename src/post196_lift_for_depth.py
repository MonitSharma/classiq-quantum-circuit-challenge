"""Anneal the kernel's integer phase lift against compiled depth, not sparsity.

Every previous lift search in this repository minimised the number of nonzero
Walsh coefficients, on the assumption that depth follows sparsity.  It does not:
the beam scheduler turns 69 terms into 43 layers and its occupancy bound is 31,
so how the terms are *distributed* over wires matters as much as how many there
are.  A 75-term lift whose parities chain well can schedule shallower than a
69-term lift whose parities do not.

So this anneals over the same freedoms -- adding even multiples of any Boolean
monomial, which changes no reachable phase, and arbitrary values on the code
pairs no coordinate reaches -- but scores each candidate by actually compiling
it with a few beam seeds.  Expensive per step, which is why the move set is kept
small and the seed count low, with the shortlist recompiled properly at the end.
"""
import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Operator

from depth_parity_network import walsh as walsh1
from distributed_frame_search import native
from post218_beam_phase import psynth

MONO = [np.array([1.0 if (m & ~w) == 0 else 0.0 for w in range(256)]) for m in range(256)]
# A cheap beam is used to *rank* candidate lifts and an expensive one to compile
# the winner; the cheap ranking is deterministic, so candidates are compared
# like for like even though its absolute depths are a layer or two higher.
PROBE = [(24, 8, 5.0, 0.35)]
CONFIGS = [(64, 14, 5.0, 0.35), (80, 16, 7.0, 0.45)]


def compile_depth(phases, seeds, configs=CONFIGS):
    co = walsh1(phases)
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    best = None
    for seed in seeds:
        for beam, branch, alpha, timew in configs:
            q = native(psynth(8, targets, seed=seed, beam=beam, branch=branch, alpha=alpha,
                              timew=timew, global_phase=float(co[0])))
            score = (q.depth(), q.count_ops().get('cx', 0))
            if best is None or score < best[0]:
                best = (score, q, len(targets))
    return best


def verify(circuit, phases):
    op = Operator(qasm2.loads(qasm2.dumps(circuit))).data
    want = np.diag(np.exp(1j * phases))
    overlap = np.vdot(want, op)
    return float(np.max(abs(op - overlap / abs(overlap) * want)))


def run(outdir, steps, seed, spec, probe_seeds, final_seeds):
    outdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    base = np.array(spec['phases'], float)
    reachable = set(spec['reachable'])
    free = [w for w in range(256) if w not in reachable]

    current = base.copy()
    score = compile_depth(current * math.pi, range(probe_seeds), PROBE)[0]
    best, best_vec, best_score = score, current.copy(), score
    history = []
    for step in range(steps):
        delta = np.zeros(256)
        if free and rng.random() < 0.3:
            delta[rng.choice(free)] = rng.choice((1, -1, 2, -2))
        else:
            delta = rng.choice((2, -2, 4, -4)) * MONO[rng.randrange(256)]
        trial = current + delta
        got = compile_depth(trial * math.pi, range(probe_seeds), PROBE)[0]
        temp = 0.4 + 2.5 * (1 - (step % 120) / 120)
        if got <= score or rng.random() < math.exp((score[0] - got[0]) / temp):
            current, score = trial, got
            if got < best:
                best, best_vec, best_score = got, trial.copy(), got
                history.append(dict(step=step, depth=got[0], cx=got[1]))
                print(history[-1], flush=True)
    phases = best_vec * math.pi
    final = compile_depth(phases, range(final_seeds))
    error = verify(final[1], phases)
    assert error < 1e-10, error
    for w in sorted(reachable):
        assert abs(best_vec[w] - base[w]) % 2 < 1e-6, 'lift changed a reachable phase'
    (outdir / 'lift_depth.json').write_text(json.dumps(
        dict(seed=seed, steps=steps, probe_depth=list(best_score), final_depth=list(final[0]),
             terms=final[2], error=error, phases=best_vec.tolist(), improvements=history),
        indent=1) + '\n')
    (outdir / 'kernel.qasm').write_text(qasm2.dumps(final[1]))
    print('final', final[0], 'terms', final[2], 'error', error, flush=True)
    return final


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--spec', type=Path, required=True)
    p.add_argument('--steps', type=int, default=250)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--probe-seeds', type=int, default=3)
    p.add_argument('--final-seeds', type=int, default=40)
    a = p.parse_args()
    run(a.outdir, a.steps, a.seed, json.loads(a.spec.read_text()), a.probe_seeds, a.final_seeds)
