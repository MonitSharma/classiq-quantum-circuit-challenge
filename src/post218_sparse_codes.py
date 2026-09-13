"""Search feature codes that are cheap to load rather than class-constant.

The kernel only needs `code(v)` to determine the row (or column) class, so the
code partition may be *finer* than the class partition.  Earlier searches fixed
one constant label per (raw parity, class) cell, which forced the loaded bits to
be unions of geometric cells and therefore Walsh-dense.  Here the three loaded
bits are free Boolean functions and the class-determination requirement is a
constraint, which lets annealing trade refinement for spectral sparsity.

Loader cost is the number of Walsh terms of the loaded angle tables: that is
exactly the number of Rz rotations any parity-network lookup has to emit.
"""
import argparse
import json
import math
import random
from pathlib import Path

import numpy as np

from two_stage_oracle import ROWCLS, COLCLS

H = np.array([[1.0]])
for _ in range(6):
    H = np.block([[H, H], [H, -H]])
H = H / 64.0


def raw_values(rhos):
    return np.array([sum((((v & r).bit_count() & 1) << i) for i, r in enumerate(rhos))
                     for v in range(64)], dtype=np.int64)


def conflicts(code, cls):
    """Number of (code value, class) groupings beyond one class per code."""
    seen = {}
    for v in range(64):
        seen.setdefault(int(code[v]), set()).add(cls[v])
    return sum(len(s) - 1 for s in seen.values())


def support(g):
    return int((np.abs(g @ H.T) > 1e-9).sum())


def anneal(cls, rhos, iters, seed, penalty=40.0):
    rng = random.Random(seed)
    raw = raw_values(rhos)
    k = len(rhos)
    g = np.zeros((3, 64))
    # start from a class-constant labelling so the constraint begins satisfied
    order = {}
    for v in range(64):
        key = (int(raw[v]), cls[v])
        if key not in order:
            order[key] = len([1 for kk in order if kk[0] == key[0]])
    for v in range(64):
        lab = order[(int(raw[v]), cls[v])]
        if lab > 7:
            return None
        for j in range(3):
            g[j, v] = (lab >> j) & 1

    def code_of(gg):
        return raw + (gg[0] * 2 + gg[1] * 4 + gg[2] * 8).astype(np.int64) * (1 << k)

    def cost(gg):
        return support(gg) + penalty * conflicts(code_of(gg), cls)

    cur = cost(g)
    best, bestg = cur, g.copy()
    for it in range(iters):
        j = rng.randrange(3)
        v = rng.randrange(64)
        g[j, v] = 1 - g[j, v]
        val = cost(g)
        temp = 0.25 + 3.0 * (1 - (it % 3000) / 3000)
        if val <= cur or rng.random() < math.exp((cur - val) / temp):
            cur = val
            if val < best and conflicts(code_of(g), cls) == 0:
                best, bestg = val, g.copy()
        else:
            g[j, v] = 1 - g[j, v]
    if conflicts(code_of(bestg), cls):
        return None
    return support(bestg), bestg.astype(int).tolist()


def run(outdir, iters, seeds):
    outdir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, cls in (('y', ROWCLS), ('x', COLCLS)):
        rows = []
        singles = [(r,) for r in range(1, 64)]
        pairs = [(a, b) for a in range(1, 64) for b in range(a + 1, 64)]
        random.Random(0).shuffle(pairs)
        for rhos in singles + pairs[:400]:
            for s in range(seeds):
                got = anneal(cls, rhos, iters, s)
                if got:
                    rows.append(dict(rhos=list(rhos), support=got[0], bits=got[1]))
        rows.sort(key=lambda r: (r['support'], len(r['rhos'])))
        report[name] = rows[:20]
        print(name, [(r['support'], r['rhos']) for r in rows[:8]], flush=True)
    (outdir / 'codes.json').write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--iters', type=int, default=20000)
    p.add_argument('--seeds', type=int, default=2)
    a = p.parse_args()
    run(a.outdir, a.iters, a.seeds)
