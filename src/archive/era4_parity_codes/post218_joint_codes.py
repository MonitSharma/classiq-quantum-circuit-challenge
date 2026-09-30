"""Joint class-code search against a depth-calibrated cost, not a degree proxy.

Two quantities decide the oracle depth in this architecture:

* the number of Walsh terms of the three loaded angle tables, which sets the
  loader depth (measured: 174 terms -> 77 layers, 94 terms -> 62 layers), and
* the number of parity terms of the eight-wire kernel, which sets the kernel
  depth (measured: 69 terms -> 45 layers, 170 terms -> 99 layers).

Earlier searches optimised a per-monomial degree weight, which ranks kernels
but says nothing about the loaders, and the two pull in opposite directions: the
Walsh-sparsest codes found so far raise the kernel from 69 to 170 terms.  This
module anneals both labellings together against the linear fits above and keeps
the whole Pareto front so candidates can be compiled and compared exactly.
"""
import argparse
import json
import math
import random
from pathlib import Path

import numpy as np

from two_stage_oracle import ROWCLS, COLCLS, logo

ORDER = sorted(range(256), key=lambda m: (m.bit_count(), m))
EVAL = [sum(1 << i for i, m in enumerate(ORDER) if m & ~w == 0) for w in range(256)]

H6 = np.array([[1.0]])
for _ in range(6):
    H6 = np.block([[H6, H6], [H6, -H6]])
H6 = H6 / 64.0
H8 = np.array([[1.0]])
for _ in range(8):
    H8 = np.block([[H8, H8], [H8, -H8]])
H8 = H8 / 256.0

LOADER_A, LOADER_B = 44.0, 0.19
KERNEL_A, KERNEL_B = 8.0, 0.53
LIFT = 0.78          # measured reduction of kernel parity terms by the integer lift


def cell_map(cls, rho):
    out = {}
    for v in range(64):
        out.setdefault(((v & rho).bit_count() & 1, cls[v]), []).append(v)
    return out


def codes_from(cellmap, lab, rho):
    code = [0] * 64
    for key, members in cellmap.items():
        for v in members:
            code[v] = key[0] | (lab[key] << 1)
    return code


def loader_terms(code):
    table = np.array([[math.pi * ((code[v] >> b) & 1) for v in range(64)] for b in range(1, 4)])
    return int((np.abs(table @ H6.T) > 1e-9).sum())


def kernel_solution(ycode, xcode):
    want = {}
    for y in range(64):
        for x in range(64):
            key = ycode[y] | (xcode[x] << 4)
            value = 1 if logo(x, y) else 0
            if want.setdefault(key, value) != value:
                return None
    piv = {}
    for w, value in want.items():
        row, rhs = EVAL[w], value
        while row:
            i = (row & -row).bit_length() - 1
            if i in piv:
                a, b = piv[i]
                row ^= a
                rhs ^= b
            else:
                piv[i] = (row, rhs)
                break
        else:
            if rhs:
                return None
    sol = 0
    for i in sorted(piv, reverse=True):
        row, rhs = piv[i]
        if ((row & sol).bit_count() & 1) ^ rhs:
            sol |= 1 << i
    counts = np.array([(EVAL[w] & sol).bit_count() for w in range(256)], float)
    spectrum = counts @ H8.T
    terms = [ORDER[i] for i in range(256) if sol >> i & 1]
    return int((np.abs(spectrum) > 1e-9).sum()), terms


def score(tl, tk):
    return 2 * (LOADER_A + LOADER_B * tl) + KERNEL_A + KERNEL_B * LIFT * tk


def search(outdir, steps, seed, start=None):
    outdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    ycells, xcells = cell_map(ROWCLS, 32), cell_map(COLCLS, 48)
    sides = []
    for cells in (ycells, xcells):
        fibers = {}
        for k in cells:
            fibers.setdefault(k[0], []).append(k)
        assert all(len(v) <= 8 for v in fibers.values())
        lab = {}
        for group in fibers.values():
            for i, k in enumerate(group):
                lab[k] = i
        sides.append((cells, fibers, lab))
    if start:
        for side, key in enumerate(('ylab', 'xlab')):
            given = {tuple(map(int, k.split(','))): v for k, v in start[key].items()}
            assert set(given) == set(sides[side][2]), 'start labelling does not match the cells'
            sides[side][2].update(given)

    def evaluate():
        yc = codes_from(sides[0][0], sides[0][2], 32)
        xc = codes_from(sides[1][0], sides[1][2], 48)
        got = kernel_solution(yc, xc)
        if got is None:
            return None
        tl = max(loader_terms(yc), loader_terms(xc))
        return tl, got[0], yc, xc, got[1]

    state = evaluate()
    cur = score(state[0], state[1])
    best = cur
    front = {}
    records = []
    for step in range(steps):
        side = rng.randrange(2)
        cells, fibers, lab = sides[side]
        group = rng.choice(list(fibers.values()))
        a = rng.choice(group)
        value = rng.randrange(8)
        other = next((k for k in group if lab[k] == value), None)
        prev = lab[a]
        lab[a] = value
        if other is not None:
            lab[other] = prev
        got = evaluate()
        val = score(got[0], got[1]) if got else 1e9
        temp = 1.0 + 12.0 * (1 - (step % 1500) / 1500)
        if val <= cur or rng.random() < math.exp(min(0.0, (cur - val) / temp)):
            cur, state = val, got
            key = (got[0], got[1])
            if key not in front:
                front[key] = (json.dumps({f"{k[0]},{k[1]}": v for k, v in sides[0][2].items()}),
                              json.dumps({f"{k[0]},{k[1]}": v for k, v in sides[1][2].items()}))
            if val < best:
                best = val
                records.append(dict(step=step, loader_terms=got[0], kernel_terms=got[1],
                                    predicted_depth=round(val, 1)))
                print(records[-1], flush=True)
        else:
            lab[a] = prev
            if other is not None:
                lab[other] = value
    pareto = []
    for (tl, tk), labs in sorted(front.items()):
        if not any(o[0] <= tl and o[1] <= tk and o != (tl, tk) for o in front):
            pareto.append(dict(loader_terms=tl, kernel_terms=tk, predicted_depth=round(score(tl, tk), 1),
                               ylab=json.loads(labs[0]), xlab=json.loads(labs[1])))
    pareto.sort(key=lambda r: r['predicted_depth'])
    (outdir / 'pareto.json').write_text(json.dumps(pareto[:40], indent=1) + '\n')
    (outdir / 'search.json').write_text(json.dumps(dict(seed=seed, steps=steps,
                                                        improvements=records), indent=1) + '\n')
    print('pareto size', len(pareto), 'best predicted', pareto[0]['predicted_depth'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--steps', type=int, default=20000)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--start', type=Path, default=None)
    a = p.parse_args()
    begin = json.loads(a.start.read_text()) if a.start else None
    search(a.outdir, a.steps, a.seed, begin)
