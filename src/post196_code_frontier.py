"""Bounded heuristic frontier of loader and kernel terms over class codes.

The pool, one representative per total, and final shortlist discard candidates.
Kernel scoring uses one ANF completion, not an optimal integer phase lift.
This search cannot establish an architecture-wide depth lower bound.

A four-bit-per-side code is one raw parity plus a three-bit label per
(raw parity, class) cell.  The three loaded bits are then the indicator
functions of three cell subsets S0, S1, S2, and the only requirement is that
within each raw fiber the triple separates the cells -- a 36-element set-cover.

That makes the search tractable without annealing: enumerate S0 and S1 over the
spectrally sparsest subsets, and for each pair solve for S2 exactly.  The pairs
S2 must still separate form a graph on the cells; S2 exists iff that graph is
bipartite, and then S2 is fixed per connected component up to complement, so the
minimum-support choice is found by trying the 2^(components) orientations.

Loader depth scales with the total Walsh support of the three bits and kernel
depth with the kernel's parity-term count, so the frontier of the two is what
decides the achievable oracle depth.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from two_stage_oracle import ROWCLS, COLCLS, logo

H6 = np.array([[1.0]])
for _ in range(6):
    H6 = np.block([[H6, H6], [H6, -H6]])
H6 = H6 / 64.0

ORDER8 = sorted(range(256), key=lambda m: (m.bit_count(), m))
EVAL8 = [sum(1 << i for i, m in enumerate(ORDER8) if m & ~w == 0) for w in range(256)]
H8 = np.array([[1.0]])
for _ in range(8):
    H8 = np.block([[H8, H8], [H8, -H8]])
H8 = H8 / 256.0


def cells_of(cls, rho):
    cells, order = {}, []
    for v in range(64):
        key = ((v & rho).bit_count() & 1, cls[v])
        if key not in cells:
            cells[key] = len(order)
            order.append(key)
        cells[key] = cells[key]
    members = [[] for _ in order]
    for v in range(64):
        members[cells[((v & rho).bit_count() & 1, cls[v])]].append(v)
    return order, members


def supports_and_separations(order, members):
    m = len(order)
    indicator = np.zeros((1 << m, 64))
    for s in range(1 << m):
        for c in range(m):
            if s >> c & 1:
                indicator[s, members[c]] = 1.0
    support = (np.abs(indicator @ H6.T) > 1e-9).sum(axis=1)
    pairs = [(i, j) for i in range(m) for j in range(i + 1, m)
             if order[i][0] == order[j][0]]
    sep = np.zeros(1 << m, dtype=np.int64)
    for k, (i, j) in enumerate(pairs):
        differ = (((np.arange(1 << m) >> i) & 1) != ((np.arange(1 << m) >> j) & 1))
        sep |= differ.astype(np.int64) << k
    return support.astype(int), sep, pairs


def complete(missing, pairs, m):
    """Minimum-support subset separating every pair in `missing`, or None."""
    adj = [[] for _ in range(m)]
    for k, (i, j) in enumerate(pairs):
        if missing >> k & 1:
            adj[i].append(j)
            adj[j].append(i)
    colour = [-1] * m
    comps = []
    for start in range(m):
        if colour[start] != -1 or not adj[start]:
            continue
        stack, comp = [start], []
        colour[start] = 0
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if colour[v] == -1:
                    colour[v] = 1 - colour[u]
                    stack.append(v)
                elif colour[v] == colour[u]:
                    return None
        comps.append(comp)
    options = [0]
    for comp in comps:
        side = sum(1 << u for u in comp if colour[u] == 0)
        other = sum(1 << u for u in comp if colour[u] == 1)
        options = [o | side for o in options] + [o | other for o in options]
    free = [u for u in range(m) if not adj[u]]
    return options, free


def kernel_terms(ycode, xcode):
    want = {}
    for y in range(64):
        for x in range(64):
            key = ycode[y] | (xcode[x] << 4)
            value = 1 if logo(x, y) else 0
            if want.setdefault(key, value) != value:
                return None
    piv = {}
    for w, value in want.items():
        row, rhs = EVAL8[w], value
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
    counts = np.array([(EVAL8[w] & sol).bit_count() for w in range(256)], float)
    return int((np.abs(counts @ H8.T) > 1e-9).sum())


def completion_subsets(options, free):
    """Include both values of every unconstrained cell in every orientation."""
    for assignment in range(1 << len(free)):
        extra = sum(((assignment >> i) & 1) << cell for i, cell in enumerate(free))
        for base in options:
            yield base | extra


def side_frontier(cls, rho, pool, keep):
    order, members = cells_of(cls, rho)
    m = len(order)
    if any(sum(1 for k in order if k[0] == f) > 8 for f in (0, 1)):
        return []
    support, sep, pairs = supports_and_separations(order, members)
    full = (1 << len(pairs)) - 1
    ranked = np.argsort(support)[:pool]
    best = {}
    for a in ranked:
        sa, pa = int(support[a]), int(sep[a])
        for b in ranked:
            if b <= a:
                continue
            total_ab = sa + int(support[b])
            missing = full & ~(pa | int(sep[b]))
            got = complete(missing, pairs, m)
            if got is None:
                continue
            options, free = got
            for cand in completion_subsets(options, free):
                total = int(total_ab + int(support[cand]))
                labels = [0] * m
                for c in range(m):
                    labels[c] = ((a >> c & 1) | ((b >> c & 1) << 1) | ((cand >> c & 1) << 2))
                if len(set(labels[c] for c in range(m) if order[c][0] == 0)) != \
                        sum(1 for k in order if k[0] == 0):
                    continue
                if len(set(labels[c] for c in range(m) if order[c][0] == 1)) != \
                        sum(1 for k in order if k[0] == 1):
                    continue
                code = [0] * 64
                for c in range(m):
                    for v in members[c]:
                        code[v] = int(order[c][0]) | (int(labels[c]) << 1)
                key = total
                if key not in best or best[key][0] > total:
                    best[key] = (total, code)
    rows = sorted(best.values())[:keep]
    return rows


def run(outdir, pool, keep):
    outdir.mkdir(parents=True, exist_ok=True)
    ys = side_frontier(ROWCLS, 32, pool, keep)
    print('y candidates', len(ys), 'best support', ys[0][0] if ys else None, flush=True)
    xs = []
    for rho in (16, 48, 6, 60):
        got = side_frontier(COLCLS, rho, pool, keep)
        for total, code in got:
            xs.append((total, rho, code))
    xs.sort()
    print('x candidates', len(xs), 'best support', xs[0][0] if xs else None, flush=True)
    rows = []
    for ty, ycode in ys[:60]:
        for tx, rho, xcode in xs[:60]:
            tk = kernel_terms(ycode, xcode)
            if tk is None:
                continue
            rows.append(dict(loader_terms=int(max(ty, tx)), y_terms=int(ty), x_terms=int(tx),
                             kernel_terms=int(tk), x_rho=int(rho),
                             predicted=round(2 * (13 + max(ty, tx) / 3) + 8 + 0.53 * tk, 1),
                             ycode=ycode, xcode=xcode))
    rows.sort(key=lambda r: r['predicted'])
    (outdir / 'frontier.json').write_text(json.dumps(rows[:40], indent=1) + '\n')
    for r in rows[:10]:
        print({k: r[k] for k in ('loader_terms', 'kernel_terms', 'x_rho', 'predicted')}, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--pool', type=int, default=300)
    p.add_argument('--keep', type=int, default=200)
    a = p.parse_args()
    run(a.outdir, a.pool, a.keep)
