"""Joint class-code search scored by loader sweep depth, not only kernel ANF degree.

The existing searches (`post258_raw_parity_codes`, `post221_joint_cost_search`)
score a candidate code by the kernel's ANF degree or Walsh count, because
`distributed_ucry.structured_ucry` walks a fixed 24-parity skeleton whose depth
barely moves when the code's spectrum is sparse.  The skeleton's *sparse* mode
does respond, but to the shape of the spectrum rather than its size: each stage
costs the longest host chain, so what matters is how evenly the nonzero Walsh
masks spread over the twenty-four (output, high-mask) host groups.

This module scores a code by that quantity directly and anneals the two label
tables against `2 * loader + kernel`, the way the finished oracle's depth is
actually composed.
"""
import argparse
import itertools
import json
import math
import random
import time
from pathlib import Path

import numpy as np

import two_stage_oracle as ts
from post258_raw_parity_codes import cells, poly
from post258_two_stage_anf import ORDER, encode, decode

H64 = np.array([[(-1) ** ((a & b).bit_count() % 2) for b in range(64)] for a in range(64)], int)
H256 = np.array([[(-1) ** ((a & b).bit_count() % 2) for b in range(256)] for a in range(256)], int)


def _walk_table():
    """Shortest closed walk 0 -> S -> 0 on the three-bit cube, for every S."""
    table = [0] * 256
    for bits in range(256):
        masks = [m for m in range(8) if bits >> m & 1]
        if not masks:
            continue
        best = None
        for perm in itertools.permutations(masks):
            cost = cur = 0
            for m in perm:
                cost += (cur ^ m).bit_count()
                cur = m
            cost += cur.bit_count()
            best = cost if best is None else min(best, cost)
        table[bits] = best
    return table


WALK = _walk_table()


def _stage_forms():
    out = []
    for stage in range(4):
        gray = stage ^ (stage >> 1)
        shifts = [sum(((gray >> k) & 1) << ((i + k + 1) % 3) for k in range(2)) for i in range(3)]
        out.append([(i, (1 << i) ^ shifts[i]) for i in range(3)]
                   + [(i, shifts[i]) for i in range(3)])
    return out


STAGES = _stage_forms()
SPLITS = [(h, tuple(i for i in range(6) if i not in h))
          for h in itertools.combinations(range(6), 3)]


def loader_cost(code):
    """Estimated sparse-skeleton loader depth, minimised over the high/low split."""
    bits = np.array([[(c >> j) & 1 for c in code] for j in range(3)])
    spec = bits @ H64                      # nonzero exactly where the Walsh coefficient is
    best = None
    for high, low in SPLITS:
        occ = np.zeros((3, 8), dtype=int)   # bitset of low-masks per (output, high-mask)
        for j in range(3):
            for m in np.flatnonzero(spec[j]):
                m = int(m)
                mh = sum(((m >> high[k]) & 1) << k for k in range(3))
                ml = sum(((m >> low[k]) & 1) << k for k in range(3))
                occ[j][mh] |= 1 << ml
        total = 12
        for forms in STAGES:
            chains = []
            cx = 0
            for j, mh in forms:
                bitset = int(occ[j][mh])
                w = WALK[bitset]
                chains.append(w + bitset.bit_count())
                cx += w
            total += max(max(chains), -(-cx // 3))
        if best is None or total < best:
            best = total
    return best


def kernel_masks(terms):
    """Walsh support of the integer monomial count, which is what the kernel emits.

    The phase only matters modulo two turns, and the unreduced integer sum has a
    much sparser spectrum than its mod-2 reduction, so `post258_raw_parity_codes`
    synthesises the integer table.  Scoring the reduced table would misrank codes.
    """
    table = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], int)
    return int(np.count_nonzero(table @ H256))


def codes_of(lab, cls, mask):
    return [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]


def valid_masks(cls):
    out = []
    for mask in range(1, 64):
        groups = {}
        for v, c in enumerate(cls):
            groups.setdefault(((v & mask).bit_count() % 2, c), []).append(v)
        if max(sum(k[0] == b for k in groups) for b in (0, 1)) <= 8:
            out.append(mask)
    return out


def evaluate(ylab, xlab, ymask, xmask, ycell, xcell, kernel_weight):
    ly = loader_cost(codes_of(ylab, ts.ROWCLS, ymask))
    lx = loader_cost(codes_of(xlab, ts.COLCLS, xmask))
    sol = poly(ylab, xlab, ycell, xcell)
    terms = [m for i, m in enumerate(ORDER) if sol >> i & 1]
    k = kernel_masks(terms)
    return 2 * max(ly, lx) + kernel_weight * k, (ly, lx, k), terms


def random_labels(cell, rng):
    lab = {}
    for b in (0, 1):
        keys = [k for k in cell if k[0] == b]
        values = list(range(8))
        rng.shuffle(values)
        lab.update(zip(keys, values))
    return lab


def run(outdir, steps, seed, ymask, xmask, kernel_weight, temperature, start):
    outdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    ycell, xcell = cells(ts.ROWCLS, ymask), cells(ts.COLCLS, xmask)
    if start is not None:
        rec = json.loads(Path(start).read_text())
        labs = [decode(rec['ylab']), decode(rec['xlab'])]
    else:
        labs = [random_labels(ycell, rng), random_labels(xcell, rng)]
    cur, parts, terms = evaluate(*labs, ymask, xmask, ycell, xcell, kernel_weight)
    best = cur
    rows = []
    t0 = time.monotonic()
    for step in range(steps):
        side = rng.randrange(2)
        lab = labs[side]
        previous = lab.copy()
        keys = list(lab)
        if rng.random() < 0.4:
            control, target = rng.sample(range(3), 2)
            half = rng.choice([0, 1, None])
            kind = rng.randrange(2)
            for key in keys:
                if half is None or key[0] == half:
                    lab[key] ^= (1 if kind == 0 else lab[key] >> control & 1) << target
        else:
            a = rng.choice(keys)
            value = rng.randrange(8)
            other = next((k for k in keys if k[0] == a[0] and lab[k] == value), None)
            prev = lab[a]
            lab[a] = value
            if other is not None:
                lab[other] = prev
        val, p, t = evaluate(*labs, ymask, xmask, ycell, xcell, kernel_weight)
        temp = 1 + temperature * (1 - (step % 2000) / 2000) ** 2
        if val <= cur or rng.random() < math.exp(min(0, (cur - val) / temp)):
            cur, parts, terms = val, p, t
        else:
            lab.clear()
            lab.update(previous)
            continue
        if cur < best:
            best = cur
            row = dict(step=step, seed=seed, cost=cur, loader=parts[:2], kernel_support=parts[2],
                       ymask=ymask, xmask=xmask, terms=terms,
                       ylab=encode(labs[0]), xlab=encode(labs[1]),
                       temperature=temperature, macros=True)
            rows.append(row)
            (outdir / 'best.json').write_text(json.dumps(row, indent=2) + '\n')
            print('best step=%d cost=%.1f loaders=%s kernel=%d' % (step, cur, parts[:2], parts[2]),
                  flush=True)
    (outdir / 'history.json').write_text(json.dumps(
        dict(seconds=time.monotonic() - t0, ymask=ymask, xmask=xmask,
             kernel_weight=kernel_weight, rows=rows), indent=2) + '\n')
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--steps', type=int, default=4000)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--ymask', type=int, default=32)
    p.add_argument('--xmask', type=int, default=48)
    p.add_argument('--kernel-weight', type=float, default=0.43)
    p.add_argument('--temperature', type=float, default=12.0)
    p.add_argument('--start', type=Path)
    a = p.parse_args()
    run(a.outdir, a.steps, a.seed, a.ymask, a.xmask, a.kernel_weight, a.temperature, a.start)
