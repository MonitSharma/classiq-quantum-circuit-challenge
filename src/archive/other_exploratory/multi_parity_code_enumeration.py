"""Exhaustive enumeration of 4-bit class codes split as (r parities + (4-r) labels).

The v1.34 closure covered only r=1 (one parity, three label bits).  A 4-bit code
can also be (2 parities + 2 label bits) or (3 parities + 1 label bit).  If the
label then depends on fewer than six address variables, the loader address
shortens while the 8-wire kernel is preserved.

Criterion (exact):
  code(t) = (p_1(t)..p_r(t), L(t|_S)), L a function of the projection z = t|_S.
  Code must separate classes.  For fixed z the label is fixed, so two classes
  meeting at one projection must have different parity vectors.  Nodes are
  (class, parity-vector) pairs; nodes sharing a projection must share a label
  (union-find).  Then no component may carry two nodes of the same cell, and
  each cell may host at most 2^(4-r) components.
"""
import itertools, sys
sys.path.insert(0, 'src')
import two_stage_oracle as ts


def parity_vectors(t, masks):
    return tuple((t & m).bit_count() & 1 for m in masks)


def valid(side, Sbits, masks):
    cls = ts.ROWCLS if side == 'y' else ts.COLCLS
    r = len(masks)
    Smask = sum(1 << b for b in Sbits)
    nodes = {}
    for t in range(64):
        nodes.setdefault((cls[t], parity_vectors(t, masks)), set()).add(t & Smask)
    keys = list(nodes)
    parent = {k: k for k in keys}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    byproj = {}
    for k in keys:
        for z in nodes[k]:
            byproj.setdefault(z, []).append(k)
    for z, ks in byproj.items():
        for k in ks[1:]:
            union(ks[0], k)
    comps = {}
    for k in keys:
        comps.setdefault(find(k), []).append(k)
    for c, members in comps.items():
        cells = [m[1] for m in members]
        if len(set(cells)) != len(cells):
            return False          # two same-cell classes forced to one label
    for cell in itertools.product((0, 1), repeat=r):
        n = sum(1 for c, members in comps.items() if any(m[1] == cell for m in members))
        if n > (1 << (4 - r)):
            return False
    return True


def enumerate_axis(side):
    out = {}
    for r in (1, 2, 3):
        lab_bits = 4 - r
        for k in range(2, 7):
            hits = []
            for Sbits in itertools.combinations(range(6), k):
                for combo in itertools.combinations(range(1, 64), r):
                    if valid(side, Sbits, combo):
                        hits.append((Sbits, combo))
            out[(r, k)] = hits
    return out


if __name__ == '__main__':
    for side in ('x', 'y'):
        res = enumerate_axis(side)
        print('==== side', side)
        for (r, k), hits in sorted(res.items()):
            print(f'  r={r} parities ({4-r} label bits), label vars k={k}: {len(hits)} valid',
                  hits[:4] if hits else '')
