"""Nonlinear-quotient labels: the loader only needs the label to be constant on a
matching, not on a linear coset.

Every earlier narrow-label search (v1.34 enumeration, five-address campaign,
post190 folds) required the loaded label to be constant along an affine
direction.  The loader itself only requires the label to be a function of five
of the six address wires AFTER a reversible pre-transform, and any reversible
pre-transform induces an arbitrary perfect matching, not a coset partition.

This constructs such a matching greedily for each axis: within each parity, a
class's elements are paired with each other (so the label is constant on the
pair), and odd leftovers are paired across parities, where the parity bit
already separates them.  It then measures the real loader and kernel.
"""
import json, math, sys
from pathlib import Path
from collections import defaultdict
import numpy as np

sys.path.insert(0, 'src')
import two_stage_oracle as ts
from distributed_ucry import structured_ucry
from distributed_frame_search import native
from post185_schedule_floor import support


def classes_of(side):
    return ts.ROWCLS if side == 'y' else ts.COLCLS


def build_matching(side, parmask):
    """Return pairing: dict t -> partner, with same-parity pairs in one class."""
    cls = classes_of(side)
    par = [(t & parmask).bit_count() % 2 for t in range(64)]
    buckets = defaultdict(list)
    for t in range(64):
        buckets[(par[t], cls[t])].append(t)
    partners = {}
    leftovers = {0: [], 1: []}
    # mate same-(parity,class) elements adjacently: sort then pair consecutive
    for (v, c), members in buckets.items():
        members = sorted(members)
        i = 0
        while i + 1 < len(members):
            a, b = members[i], members[i + 1]
            partners[a] = b; partners[b] = a
            i += 2
        if i < len(members):
            leftovers[v].append(members[i])
    assert len(leftovers[0]) == len(leftovers[1]), (side, len(leftovers[0]), len(leftovers[1]))
    for a, b in zip(leftovers[0], leftovers[1]):
        partners[a] = b; partners[b] = a
    assert len(partners) == 64 and all(partners[partners[t]] == t for t in range(64))
    return partners, par


def label_from_matching(side, partners, par):
    """Assign one of 8 labels per pair, consistent per parity and per class."""
    cls = classes_of(side)
    pairs = {}
    for t in range(64):
        p = min(t, partners[t])
        pairs.setdefault(p, []).append(t)
    # constraint: for parity v, pairs containing (v,class) must be labellable so
    # that distinct classes in v get distinct labels
    lab = {}
    next_label = {}
    nxt = 0
    for p, members in sorted(pairs.items()):
        need = []
        for t in members:
            need.append((par[t], cls[t]))
        l = None
        for (v, c) in need:
            if (v, c) in next_label:
                l = next_label[(v, c)]
        if l is None:
            l = nxt % 8
            nxt += 1
        for (v, c) in need:
            if (v, c) in next_label and next_label[(v, c)] != l:
                return None
            next_label[(v, c)] = l
        lab[p] = l
    # verify: for each parity, distinct classes need distinct labels
    for v in (0, 1):
        seen = {}
        for p, members in pairs.items():
            for t in members:
                if par[t] != v:
                    continue
                key = lab[p]
                c = cls[t]
                if seen.setdefault(key, c) != c:
                    return None
    label = [lab[min(t, partners[t])] for t in range(64)]
    return label


if __name__ == '__main__':
    out = {}
    for side, masks in (('y', (32,)), ('x', (6, 16, 48, 60))):
        for pm in masks:
            partners, par = build_matching(side, pm)
            label = label_from_matching(side, partners, par)
            if label is None:
                print(side, 'mask', pm, 'matching exists but labelling failed', flush=True)
                continue
            cls = classes_of(side)
            code = [par[t] | (label[t] << 1) for t in range(64)]
            ok = all(not (cls[t] != cls[u] and code[t] == code[u])
                     for t in range(64) for u in range(64))
            # how many pairs are the linear XOR-1 pair?
            xor1 = sum(1 for t in range(0, 64, 2) if partners[t] == t + 1)
            sup = support({(par[t], cls[t]): label[t] for t in range(64)}, cls, pm) if False else None
            tab = np.array([[math.pi * ((label[t] >> b) & 1) for t in range(64)] for b in range(3)])
            best = None
            for seed in range(12):
                for sparse, ow in ((True, False), (False, True)):
                    try:
                        q = native(structured_ucry(tab, [6, 7, 8], list(range(6)), seed,
                                                   sparse=sparse, open_walk=ow))
                    except Exception:
                        continue
                    sc = (q.depth(), q.count_ops().get('cx', 0))
                    if best is None or sc < best[0]:
                        best = (sc, seed, sparse, ow)
            # walsh support proxy
            sup = 0
            for b in range(3):
                f = np.array([float(x) for x in tab[b]])
                for i in range(6):
                    for m in range(64):
                        if (m >> i) & 1:
                            f[m] += f[m ^ (1 << i)]
                sup += int(np.sum(np.abs(f) > 1e-9))
            print(f'{side} mask {pm}: separates={ok} xor1_pairs={xor1}/32 walsh_support~{sup} '
                  f'loader={best}', flush=True)
            out[f'{side}_{pm}'] = dict(separates=bool(ok), xor1=xor1, support=sup, loader=best[0],
                                       label=label, partners={str(k): v for k, v in partners.items()})
    Path('artifacts/nonlinear_label').mkdir(parents=True, exist_ok=True)
    Path('artifacts/nonlinear_label/report.json').write_text(json.dumps(out, indent=2))
