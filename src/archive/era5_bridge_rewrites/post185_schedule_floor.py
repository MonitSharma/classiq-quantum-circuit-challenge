"""Hard scheduling floor of the two-stage class-code architecture.

A layer of a width-n block can hold r rotations and c CX gates only if
r + 2c <= n, and every rotation after the first on a wire needs a CX to move that
wire onto a new parity, so r <= c in steady state.  A nine-wire loader therefore
places at most three rotations per layer and the eight-wire kernel at most 8/3.
With S the loader's Walsh support and M the kernel's integer-lift Walsh support,

    depth >= 2 * (S / 3) + M / (8/3)

for any emitter of this architecture.  This module anneals the two label tables
against that bound, which says how much room the architecture still has,
independently of how good the current emitters are.

The bound counts rotations only.  Measured circuits also pay for the CX gates
that walk between parities, and that walk gets *less* efficient as the spectrum
gets sparser, so the floor is optimistic for low-support codes.  Read it together
with `docs/POST185_ARCHITECTURE_FLOOR.md`, which records the built depths.
"""
import argparse
import json
import math
import random
from pathlib import Path

import numpy as np

import two_stage_oracle as ts
from post258_raw_parity_codes import cells, poly
from post258_two_stage_anf import ORDER, encode

H64 = np.array([[(-1) ** ((a & b).bit_count() % 2) for b in range(64)] for a in range(64)], int)
H256 = np.array([[(-1) ** ((a & b).bit_count() % 2) for b in range(256)] for a in range(256)], int)

LOADER_RATE = 3.0
KERNEL_RATE = 8.0 / 3.0
LOADER_OVERHEAD = 12.0          # four host-basis transitions per loader block


def support(lab, cls, mask):
    code = [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]
    bits = np.array([[(c >> j) & 1 for c in code] for j in range(3)])
    return int(np.count_nonzero(bits @ H64))


def kernel_masks(terms):
    table = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], int)
    return int(np.count_nonzero(table @ H256))


def floor_of(labs, ymask, xmask, ycell, xcell):
    sy = support(labs[0], ts.ROWCLS, ymask)
    sx = support(labs[1], ts.COLCLS, xmask)
    sol = poly(labs[0], labs[1], ycell, xcell)
    terms = [m for i, m in enumerate(ORDER) if sol >> i & 1]
    m = kernel_masks(terms)
    value = 2 * (max(sy, sx) / LOADER_RATE + LOADER_OVERHEAD) + m / KERNEL_RATE
    return value, (sy, sx, m), terms


def anneal(xmask, seed, steps, ymask=32, temperature=10.0):
    rng = random.Random(seed)
    ycell, xcell = cells(ts.ROWCLS, ymask), cells(ts.COLCLS, xmask)
    labs = []
    for cc in (ycell, xcell):
        lab = {}
        for b in (0, 1):
            keys = [k for k in cc if k[0] == b]
            values = list(range(8))
            rng.shuffle(values)
            lab.update(zip(keys, values))
        labs.append(lab)
    cur, parts, terms = floor_of(labs, ymask, xmask, ycell, xcell)
    best, record = cur, None
    for step in range(steps):
        lab = labs[rng.randrange(2)]
        previous = lab.copy()
        keys = list(lab)
        if rng.random() < 0.4:
            control, target = rng.sample(range(3), 2)
            half = rng.choice([0, 1, None])
            kind = rng.randrange(2)
            for k in keys:
                if half is None or k[0] == half:
                    lab[k] ^= (1 if kind == 0 else lab[k] >> control & 1) << target
        else:
            a = rng.choice(keys)
            value = rng.randrange(8)
            other = next((k for k in keys if k[0] == a[0] and lab[k] == value), None)
            prev = lab[a]
            lab[a] = value
            if other is not None:
                lab[other] = prev
        val, pp, tt = floor_of(labs, ymask, xmask, ycell, xcell)
        temp = 1 + temperature * (1 - (step % 1500) / 1500) ** 2
        if val <= cur or rng.random() < math.exp(min(0, (cur - val) / temp)):
            cur, parts, terms = val, pp, tt
        else:
            lab.clear()
            lab.update(previous)
            continue
        if cur < best:
            best = cur
            record = dict(cost=round(cur, 1), S=list(parts[:2]), M=parts[2], step=step,
                          seed=seed, ymask=ymask, xmask=xmask, temperature=temperature,
                          macros=True, terms=tt,
                          ylab=encode(labs[0]), xlab=encode(labs[1]))
    return best, record


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--steps', type=int, default=4000)
    p.add_argument('--seeds', type=int, default=6)
    a = p.parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for xmask in (6, 16, 48, 60):
        for seed in range(a.seeds):
            value, rec = anneal(xmask, seed, a.steps)
            rows.append((value, rec))
            print('xmask %2d seed %d floor %.1f S=%s M=%d'
                  % (xmask, seed, value, rec['S'], rec['M']), flush=True)
    rows.sort(key=lambda r: r[0])
    (a.outdir / 'best.json').write_text(json.dumps(rows[0][1], indent=2) + '\n')
    (a.outdir / 'report.json').write_text(json.dumps(
        [r[1] for r in rows], indent=2) + '\n')
    print('best floor %.1f' % rows[0][0], rows[0][1]['S'], rows[0][1]['M'])
