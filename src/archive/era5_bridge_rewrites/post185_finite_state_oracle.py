"""Finite-state / MTBDD structural audit of the Classiq logo phase oracle.

Reproduces the exact logo predicate, enumerates row/column classes, the
nested-interval (telescoping) decomposition, GF(2)/real/sign ranks, reduced
BDD node counts under several variable orders, and tensor-train (unfolding)
ranks.  All outputs are deterministic and saved to ``--outdir``.

This is a structural screen.  It does not, by itself, produce a competitive
quantum circuit: node count and rank are not native depth.
"""
import argparse
import json
from functools import lru_cache
from pathlib import Path

import numpy as np


def logo(x, y):
    return ((2 <= x <= 26 and 29 <= y <= 53)
            or (26 <= x <= 49 and 39 <= y <= 43)
            or (x - 55) ** 2 + (y - 41) ** 2 <= 42
            or (x - 40) ** 2 + (y - 19) ** 2 <= 72)


def mask():
    return np.array([[1 if logo(x, y) else 0 for x in range(64)]
                     for y in range(64)], dtype=np.uint8)


def row_column_classes(M):
    rows, rowcls = {}, [0] * 64
    for y in range(64):
        rowcls[y] = rows.setdefault(tuple(M[y].tolist()), len(rows))
    cols, colcls = {}, [0] * 64
    for x in range(64):
        colcls[x] = cols.setdefault(tuple(M[:, x].tolist()), len(cols))
    return rowcls, colcls, len(rows), len(cols)


def intervals(bits):
    xs = [i for i, b in enumerate(bits) if b]
    out, s, p = [], None, None
    for x in xs:
        if s is None:
            s = p = x
        elif x == p + 1:
            p = x
        else:
            out.append((s, p)); s = p = x
    if s is not None:
        out.append((s, p))
    return out


def gf2_rank(A):
    A = A.copy().astype(np.uint8)
    rows, cols = A.shape
    rk = 0
    for c in range(cols):
        piv = next((r for r in range(rk, rows) if A[r][c]), None)
        if piv is None:
            continue
        A[[rk, piv]] = A[[piv, rk]]
        for r in range(rows):
            if r != rk and A[r][c]:
                A[r] ^= A[rk]
        rk += 1
    return rk


def bdd_nodes(order):
    node_id, table = [0], {}

    def make(var, lo, hi):
        if lo == hi:
            return lo
        key = (var, lo, hi)
        if key not in table:
            node_id[0] += 1
            table[key] = node_id[0]
        return table[key]

    @lru_cache(maxsize=None)
    def bdd(at):
        for lev in range(12):
            var = order[lev]
            if at[var] == -1:
                break
        else:
            x = sum(at[i] << i for i in range(6))
            y = sum(at[i + 6] << i for i in range(6))
            return 1 if logo(x, y) else 0
        lo = list(at); lo[var] = 0
        hi = list(at); hi[var] = 1
        return make(var, bdd(tuple(lo)), bdd(tuple(hi)))

    bdd(tuple([-1] * 12))
    from collections import Counter
    widths = Counter(v for (v, _, _) in table)
    return node_id[0], dict(widths)


def unfold_rank(T, order, cut):
    P = np.transpose(T, order)
    shape = P.shape
    left = int(np.prod(shape[:cut]))
    right = int(np.prod(shape[cut:]))
    return int(np.linalg.matrix_rank(P.reshape(left, right)))


def walsh_support(vals):
    a = np.array(vals, dtype=float)
    h = 1
    n = len(a)
    while h < n:
        for i in range(0, n, 2 * h):
            lo = a[i:i + h].copy()
            hi = a[i + h:i + 2 * h].copy()
            a[i:i + h] = lo + hi
            a[i + h:i + 2 * h] = lo - hi
        h *= 2
    return int(np.sum(np.abs(a / n) > 1e-12))


def audit(outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    M = mask()
    rowcls, colcls, nrows, ncols = row_column_classes(M)

    rows_desc = {}
    seen = {}
    for y in range(64):
        c = rowcls[y]
        if c not in seen:
            seen[c] = intervals(M[y].tolist())
    cols_desc = {}
    seen_c = {}
    for x in range(64):
        c = colcls[x]
        if c not in seen_c:
            seen_c[c] = intervals(M[:, x].tolist())

    # transition sequence of row class as y goes 0..63
    seq = ''.join('ABCDEFGHIJK'[rowcls[y]] for y in range(64))

    # rank facts
    f2 = gf2_rank(M)
    S = np.array([[1 if logo(x, y) else -1 for x in range(64)]
                  for y in range(64)], dtype=float)
    real = int(np.linalg.matrix_rank(S))

    # BDD under several orders
    orders = {
        'y_then_x_LSB': [6, 7, 8, 9, 10, 11, 0, 1, 2, 3, 4, 5],
        'x_then_y_LSB': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        'interleaved': [6, 0, 7, 1, 8, 2, 9, 3, 10, 4, 11, 5],
        'x_MSB_first': [5, 4, 3, 2, 1, 0, 11, 10, 9, 8, 7, 6],
        'historical': [0, 1, 5, 2, 3, 4, 11, 10, 9, 8, 6, 7],
    }
    bdd = {name: bdd_nodes(order) for name, order in orders.items()}

    # TT ranks
    T = np.ones((2,) * 12)
    for x in range(64):
        for y in range(64):
            idx = tuple([(x >> i) & 1 for i in range(6)]
                        + [(y >> i) & 1 for i in range(6)])
            T[idx] = -1 if logo(x, y) else 1
    tt = {}
    for name, order in orders.items():
        tt[name] = [unfold_rank(T, order, c) for c in range(1, 12)]

    # interval indicator Walsh support and exact GF(2) ANF monomial counts.
    def anf_monomials(f, n=6):
        vals = [f(v) for v in range(1 << n)]
        a = np.array(vals, dtype=np.uint8)
        for b in range(n):
            for i in range(1 << n):
                if i & (1 << b):
                    a[i] ^= a[i ^ (1 << b)]
        return int(np.count_nonzero(a))

    def anf_walsh(f, n=6):
        vals = [1.0 if f(v) else 0.0 for v in range(1 << n)]
        return walsh_support(vals)

    x_preds = {
        'square[2,26]': lambda x: 2 <= x <= 26,
        'bar[27,48]': lambda x: 27 <= x <= 48,
        'D2[32,48]': lambda x: 32 <= x <= 48,
        'D1[49,61]': lambda x: 49 <= x <= 61,
    }
    x_walsh = {name: anf_walsh(f) for name, f in x_preds.items()}
    x_anf = {name: anf_monomials(f) for name, f in x_preds.items()}
    # folded 8-bit disk staircase Walsh support
    tab2 = [1.0 if (dx <= 8 and dy <= 8 and dx * dx + dy * dy <= 72) else 0.0
            for dy in range(16) for dx in range(16)]
    disk2_8bit = walsh_support(tab2)

    report = dict(
        row_classes=nrows, column_classes=ncols,
        row_class_y_membership=rows_desc, column_class_x_membership=cols_desc,
        row_class_transition_sequence=seq,
        gf2_rank=f2, real_phase_matrix_rank=real,
        bdd_nodes={k: v[0] for k, v in bdd.items()},
        bdd_max_level_width={k: max(v[1].values()) for k, v in bdd.items()},
        tt_unfolding_ranks=tt,
        interval_walsh_support=x_walsh,
        interval_anf_monomials=x_anf,
        folded_disk_8bit_walsh_support=disk2_8bit,
    )
    (outdir / 'structural_audit.json').write_text(
        json.dumps(report, indent=2, default=str))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    a = p.parse_args()
    r = audit(a.outdir)
    print(json.dumps(dict(
        row_classes=r['row_classes'], column_classes=r['column_classes'],
        gf2_rank=r['gf2_rank'], real_phase_matrix_rank=r['real_phase_matrix_rank'],
        bdd_nodes=r['bdd_nodes'],
        interval_walsh_support=r['interval_walsh_support'],
        interval_anf_monomials=r['interval_anf_monomials'],
        folded_disk_8bit_walsh_support=r['folded_disk_8bit_walsh_support']),
        indent=2))
