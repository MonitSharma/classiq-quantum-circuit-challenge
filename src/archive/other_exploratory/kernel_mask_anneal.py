"""Anneal label assignments to minimise the KERNEL mask count alone.

The v1.34 joint anneal optimised 2*(S/3 + 12) + M/(8/3), where S is the loader
Walsh support.  Measurement showed the S term is mis-weighted: S 174 -> 98 bought
only 78 -> 71 loader layers, while the M term grew 90 -> 139-188 and the full
oracle got worse.  This anneals M alone, which is the term that actually tracks
emitted kernel depth, and then measures both blocks exactly.
"""
import json, math, random, sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, 'src')
import two_stage_oracle as ts
from post185_schedule_floor import support, kernel_masks
from post258_raw_parity_codes import cells, poly
from post258_two_stage_anf import ORDER, encode, decode


def evaluate(labs, ymask, xmask, ycell, xcell):
    sy = support(labs[0], ts.ROWCLS, ymask)
    sx = support(labs[1], ts.COLCLS, xmask)
    sol = poly(labs[0], labs[1], ycell, xcell)
    terms = [m for i, m in enumerate(ORDER) if sol >> i & 1]
    return kernel_masks(terms), sy, sx, terms


def mutate(lab, keys, rng):
    if rng.random() < 0.5:
        b = rng.randrange(2)
        group = [k for k in keys if k[0] == b]
        if len(group) < 2:
            return None
        a, c = rng.sample(group, 2)
        lab[a], lab[c] = lab[c], lab[a]
        return (a, c)
    a = rng.choice(keys)
    b = a[0]
    group = [k for k in keys if k[0] == b]
    val = rng.randrange(8)
    other = next((k for k in group if lab[k] == val), None)
    prev = lab[a]
    lab[a] = val
    if other is not None and other != a:
        lab[other] = prev
    return (a, other, prev, val)


def anneal(xmask, seed, seconds, ymask=32, temperature=8.0):
    rng = random.Random(seed)
    ycell, xcell = cells(ts.ROWCLS, ymask), cells(ts.COLCLS, xmask)
    labs = []
    for cc in (ycell, xcell):
        lab = {}
        for b in (0, 1):
            keys = [k for k in cc if k[0] == b]
            vals = list(range(8)); rng.shuffle(vals)
            lab.update(zip(keys, vals))
        labs.append(lab)
    keysets = [list(l) for l in labs]
    cur, sy, sx, terms = evaluate(labs, ymask, xmask, ycell, xcell)
    best = (cur, sy, sx, [dict(l) for l in labs], terms)
    t0 = time.time()
    while time.time() - t0 < seconds:
        which = rng.randrange(2)
        lab = labs[which]
        snapshot = dict(lab)
        mv = mutate(lab, keysets[which], rng)
        if mv is None:
            continue
        val, nsy, nsx, nterms = evaluate(labs, ymask, xmask, ycell, xcell)
        temp = 1 + temperature * (1 - ((time.time() - t0) / seconds)) ** 2
        if val <= cur or rng.random() < math.exp(min(0, (cur - val) / temp)):
            cur, sy, sx, terms = val, nsy, nsx, nterms
            if val < best[0]:
                best = (val, nsy, nsx, [dict(l) for l in labs], terms)
        else:
            lab.clear(); lab.update(snapshot)
    return best


if __name__ == '__main__':
    base = json.loads(Path('artifacts/185/class_codes.json').read_text())
    ycell0, xcell0 = cells(ts.ROWCLS, 32), cells(ts.COLCLS, 48)
    m0, sy0, sx0, t0 = evaluate([decode(base['ylab']), decode(base['xlab'])], 32, 48, ycell0, xcell0)
    print(f'protected: M={m0} S=({sy0},{sx0}) terms={len(t0)}', flush=True)
    results = []
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 90
    for xmask in (48, 16, 60, 6):
        for seed in range(3):
            m, sy, sx, labs, terms = anneal(xmask, seed, seconds)
            row = dict(xmask=xmask, seed=seed, M=m, S=[sy, sx], terms=len(terms))
            results.append(row)
            print(row, flush=True)
    results.sort(key=lambda r: r['M'])
    Path('artifacts/kernel_masks_v2').mkdir(parents=True, exist_ok=True)
    Path('artifacts/kernel_masks_v2/report.json').write_text(json.dumps(
        dict(protected=dict(M=m0, S=[sy0, sx0]), rows=results), indent=2))
    print('best M', results[0]['M'], 'vs protected', m0, flush=True)
