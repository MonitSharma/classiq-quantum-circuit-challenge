"""Anneal the pair matching to minimise loaded-label Walsh support.

The loaded label need only be constant on the pairs of a perfect matching (a
reversible pre-transform quotient), not on affine cosets.  Linear frames are a
tiny subset, and the recorded linear search reported a minimum support of 94
against 174 for the protected labels, worth 78 -> 72 loader layers.  This
searches the much larger matching space for lower support.
"""
import json, math, random, sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, 'src')
import two_stage_oracle as ts
from distributed_ucry import structured_ucry
from distributed_frame_search import native


def walsh_support(label):
    sup = 0
    for b in range(3):
        f = np.array([math.pi * ((c >> b) & 1) for c in label], float)
        h = 1
        while h < 64:
            for i in range(0, 64, 2 * h):
                lo = f[i:i+h].copy(); hi = f[i+h:i+2*h].copy()
                f[i:i+h] = lo + hi; f[i+h:i+2*h] = lo - hi
            h *= 2
        sup += int(np.sum(np.abs(f) > 1e-9))
    return sup


def violation(cls, par, partners):
    """Same-parity pair must be one class."""
    v = 0
    for t in range(64):
        p = partners[t]
        if p > t and par[t] == par[p] and cls[t] != cls[p]:
            v += 1
    return v


def legal_label(cls, par, partners):
    """Greedy 8-label assignment; None if impossible."""
    pairs = {}
    for t in range(64):
        pairs.setdefault(min(t, partners[t]), []).append(t)
    assign = {}
    counter = 0
    for p, members in pairs.items():
        need = [(par[t], cls[t]) for t in members]
        lab = None
        for k in need:
            if k in assign:
                lab = assign[k]
        if lab is None:
            lab = counter; counter += 1
        for k in need:
            if k in assign and assign[k] != lab:
                return None
            assign[k] = lab
    if counter > 8:
        return None
    for v in (0, 1):
        seen = {}
        for p, members in pairs.items():
            for t in members:
                if par[t] != v:
                    continue
                key = assign[(par[t], cls[t])]
                if seen.setdefault(key, cls[t]) != cls[t]:
                    return None
    return [assign[(par[t], cls[t])] for t in range(64)]


def random_matching(rng):
    p = list(range(64)); rng.shuffle(p)
    partners = [0] * 64
    for i in range(0, 64, 2):
        partners[p[i]] = p[i+1]; partners[p[i+1]] = p[i]
    return partners


def anneal(side, parmask, seconds, seed):
    cls = ts.ROWCLS if side == 'y' else ts.COLCLS
    par = [(t & parmask).bit_count() % 2 for t in range(64)]
    rng = random.Random(seed)
    partners = random_matching(rng)
    def score(pt):
        v = violation(cls, par, pt)
        lab = legal_label(cls, par, pt)
        if lab is None:
            return 10 ** 6 + v * 1000, None
        return walsh_support(lab) + v * 1000, lab
    cur, lab = score(partners)
    best, bestpair, bestlab = cur, list(partners), lab
    t0 = time.time()
    while time.time() - t0 < seconds:
        a, b = rng.sample(range(64), 2)
        pa, pb = partners[a], partners[b]
        if pa == b:
            continue
        trial = list(partners)
        trial[a], trial[b] = pb, pa
        trial[pa], trial[pb] = b, a
        val, l = score(trial)
        temp = 1 + 6.0 * (1 - (time.time() - t0) / seconds) ** 2
        if val <= cur or rng.random() < math.exp(min(0, (cur - val) / temp)):
            partners, cur, lab = trial, val, l
            if val < best:
                best, bestpair, bestlab = val, list(trial), l
    return best, bestpair, bestlab


if __name__ == '__main__':
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    out = {}
    for side, masks in (('y', (32,)), ('x', (48, 16, 60, 6))):
        for pm in masks:
            best = None
            for seed in range(3):
                s, pt, lab = anneal(side, pm, secs, seed)
                if lab is not None and (best is None or s < best[0]):
                    best = (s, pt, lab)
            if best is None:
                print(side, pm, 'no legal matching found', flush=True)
                continue
            s, pt, lab = best
            tab = np.array([[math.pi * ((c >> b) & 1) for c in lab] for b in range(3)])
            res = None
            for seed in range(12):
                for sparse, ow in ((True, False), (False, True)):
                    try:
                        q = native(structured_ucry(tab, [6, 7, 8], list(range(6)), seed,
                                                   sparse=sparse, open_walk=ow))
                    except Exception:
                        continue
                    sc = (q.depth(), q.count_ops().get('cx', 0))
                    if res is None or sc < res[0]:
                        res = (sc, seed, sparse, ow)
            print(f'{side} mask {pm}: support {s} loader {res}', flush=True)
            out[f'{side}_{pm}'] = dict(support=s, loader=res[0], pairs=pt, label=lab)
    Path('artifacts/matching_support').mkdir(parents=True, exist_ok=True)
    Path('artifacts/matching_support/report.json').write_text(json.dumps(out, indent=2))
