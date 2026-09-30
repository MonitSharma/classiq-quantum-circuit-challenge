"""Search integer phase lifts of the eight-wire kernel for a sparser spectrum.

`exp(i*pi*f)` is unchanged when an even integer multiple of any Boolean monomial
is added to `f`, and it is unconstrained on the code pairs no coordinate reaches.
Both freedoms are explored here against the number of nonzero Walsh
coefficients, which is what the beam scheduler in `post218_beam_phase` turns
into depth (measured: 69 terms -> 45 layers, 170 terms -> 99 layers).

The earlier lift search in `post221_kernel_cube_nulls` optimised the same family
against the older one-layer greedy scheduler; rescoring matters because the two
schedulers do not rank spectra the same way.
"""
import argparse
import json
import math
import random
from pathlib import Path

import numpy as np

MONO = [np.array([1.0 if (m & ~w) == 0 else 0.0 for w in range(256)]) for m in range(256)]
H8 = np.array([[1.0]])
for _ in range(8):
    H8 = np.block([[H8, H8], [H8, -H8]])
H8 = H8 / 256.0


def terms(f):
    return int((np.abs(f @ H8.T) > 1e-9).sum())


def search(base, reachable, steps, seed, amplitudes=(2, -2, 4, -4)):
    """Anneal over even monomial lifts plus free values on unreachable points."""
    rng = random.Random(seed)
    free = [w for w in range(256) if w not in reachable]
    f = base.astype(float).copy()
    cur = terms(f)
    best, bestf = cur, f.copy()
    for step in range(steps):
        if free and rng.random() < 0.25:
            w = rng.choice(free)
            delta = np.zeros(256)
            delta[w] = rng.choice((1, -1, 2, -2))
        else:
            delta = rng.choice(amplitudes) * MONO[rng.randrange(256)]
        f += delta
        value = terms(f)
        temp = 0.6 + 6.0 * (1 - (step % 1200) / 1200)
        if value <= cur or rng.random() < math.exp((cur - value) / temp):
            cur = value
            if value < best:
                best, bestf = value, f.copy()
        else:
            f -= delta
    return best, bestf


def run(outdir, steps, seeds, spec):
    outdir.mkdir(parents=True, exist_ok=True)
    base = np.array(spec['phases'], float)
    reachable = set(spec['reachable'])
    rows = []
    champion = None
    for seed in range(seeds):
        value, f = search(base, reachable, steps, seed)
        rows.append(dict(seed=seed, terms=value))
        print(rows[-1], flush=True)
        if champion is None or value < champion[0]:
            champion = (value, f)
    for w in sorted(reachable):
        assert abs(champion[1][w] - base[w]) % 2 < 1e-6, 'lift changed a reachable phase'
    (outdir / 'lift.json').write_text(json.dumps(
        dict(rows=rows, best_terms=champion[0], phases=champion[1].tolist()), indent=1) + '\n')
    print('best', champion[0], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--spec', type=Path, required=True)
    p.add_argument('--steps', type=int, default=20000)
    p.add_argument('--seeds', type=int, default=6)
    a = p.parse_args()
    run(a.outdir, a.steps, a.seeds, json.loads(a.spec.read_text()))
