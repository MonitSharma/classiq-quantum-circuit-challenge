"""Trade loaded code bits for extra raw kernel wires.

The finished 185 oracle is `2 * loader + kernel` with one raw wire and three
loaded bits per side.  Both halves already sit at their scheduling floors, so the
only way left inside this architecture is to move information out of the loaded
code -- which costs about `Walsh support / 3` layers, twice -- and into raw
coordinate wires the kernel reads directly.  Three raw parities per side leave at
most four classes in a cell, so two loaded bits still separate every class; that
frees an ancilla and shortens both loaders, at the price of a wider kernel.

This probe measures both sides of that trade exactly: minimum loader spectra for
the reduced code, and the kernel's integer-lifted Walsh support on the wider
wire set.
"""
import argparse
import itertools
import json
import math
import random
from pathlib import Path

import numpy as np

import two_stage_oracle as ts

H64 = np.array([[(-1) ** ((a & b).bit_count() % 2) for b in range(64)] for a in range(64)], int)


def parity(v, m):
    return (v & m).bit_count() & 1


def raw_value(v, masks):
    return sum(parity(v, m) << i for i, m in enumerate(masks))


def cells(cls, masks):
    out = {}
    for v, c in enumerate(cls):
        out.setdefault((raw_value(v, masks), c), []).append(v)
    return out


def label_cells(cell, loaded, rng, tries=4000):
    """Assign an L-bit label per cell, distinct within each raw value."""
    groups = {}
    for key in cell:
        groups.setdefault(key[0], []).append(key)
    if max(len(v) for v in groups.values()) > (1 << loaded):
        return None
    best = None
    for _ in range(tries):
        lab = {}
        for raw, keys in groups.items():
            values = list(range(1 << loaded))
            rng.shuffle(values)
            lab.update(zip(keys, values))
        s = spectrum_size(lab, cell, loaded)
        if best is None or s < best[0]:
            best = (s, dict(lab))
    return best


def codes_of(lab, cell, n):
    code = [0] * 64
    for key, members in cell.items():
        for v in members:
            code[v] = lab[key]
    return code


def spectrum_size(lab, cell, loaded):
    code = codes_of(lab, cell, 64)
    bits = np.array([[(c >> j) & 1 for c in code] for j in range(loaded)])
    return int(np.count_nonzero(bits @ H64))


def kernel_polynomial(ykeys, xkeys, ycode_of, xcode_of, ywidth, xwidth, ycell, xcell):
    n = ywidth + xwidth
    size = 1 << n
    order = sorted(range(size), key=lambda m: (m.bit_count(), m))
    index = {m: i for i, m in enumerate(order)}
    evalrow = [0] * size
    for w in range(size):
        evalrow[w] = sum(1 << index[m] for m in order if m & ~w == 0)
    piv = {}
    for yk in ykeys:
        for xk in xkeys:
            w = ycode_of[yk] | (xcode_of[xk] << ywidth)
            row = evalrow[w]
            rhs = int(ts.logo(xcell[xk][0], ycell[yk][0]))
            while row:
                i = (row & -row).bit_length() - 1
                if i in piv:
                    a, b = piv[i]
                    row ^= a
                    rhs ^= b
                else:
                    piv[i] = (row, rhs)
                    break
            assert row or rhs == 0, 'code does not separate the classes'
    sol = 0
    for i in sorted(piv, reverse=True):
        row, rhs = piv[i]
        if ((row & sol).bit_count() & 1) ^ rhs:
            sol |= 1 << i
    return [order[i] for i in range(size) if sol >> i & 1], n


def walsh_support(terms, n):
    size = 1 << n
    table = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(size)], float)
    a = table.copy()
    h = 1
    while h < size:
        for i in range(0, size, 2 * h):
            lo = a[i:i + h].copy()
            hi = a[i + h:i + 2 * h].copy()
            a[i:i + h] = lo + hi
            a[i + h:i + 2 * h] = lo - hi
        h *= 2
    return int(np.count_nonzero(np.abs(a) > 1e-9))


def loader_depth(support, loaded):
    hosts = 3 + loaded
    rate = min(3.0, hosts / 2.0)
    stages = -(-8 * loaded // hosts)
    return support / rate + 5 * stages


def kernel_depth(k, wires, spare):
    return k / max(1.0, (wires + spare) / 3.0)


def probe(ymasks, xmasks, loaded, seed=0, tries=3000):
    rng = random.Random(seed)
    ycell, xcell = cells(ts.ROWCLS, ymasks), cells(ts.COLCLS, xmasks)
    ybest = label_cells(ycell, loaded, rng, tries)
    xbest = label_cells(xcell, loaded, rng, tries)
    if ybest is None or xbest is None:
        return None
    ywidth = len(ymasks) + loaded
    xwidth = len(xmasks) + loaded
    ycode_of = {k: k[0] | (ybest[1][k] << len(ymasks)) for k in ycell}
    xcode_of = {k: k[0] | (xbest[1][k] << len(xmasks)) for k in xcell}
    terms, n = kernel_polynomial(list(ycell), list(xcell), ycode_of, xcode_of,
                                 ywidth, xwidth, ycell, xcell)
    k = walsh_support(terms, n)
    spare = 6 - 2 * loaded
    ld = max(loader_depth(ybest[0], loaded), loader_depth(xbest[0], loaded))
    kd = kernel_depth(k, n, spare)
    return dict(ymasks=ymasks, xmasks=xmasks, loaded=loaded, y_support=ybest[0],
                x_support=xbest[0], kernel_masks=k, kernel_wires=n, spare=spare,
                loader_depth=round(ld, 1), kernel_depth=round(kd, 1),
                total=round(2 * ld + kd, 1), anf_terms=len(terms),
                max_degree=max(m.bit_count() for m in terms) if terms else 0)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--tries', type=int, default=3000)
    a = p.parse_args()
    configs = [
        ([32], [48], 3),
        ([32], [16], 3),
        ([8, 32], [1, 16], 3),
        ([8, 20, 32], [1, 16, 44], 2),
        ([8, 20, 32], [1, 16, 45], 2),
        ([8, 20, 40], [1, 16, 60], 2),
    ]
    for ym, xm, loaded in configs:
        try:
            r = probe(ym, xm, loaded, tries=a.tries)
        except AssertionError as exc:
            print(ym, xm, loaded, 'infeasible:', exc)
            continue
        if r is None:
            print(ym, xm, loaded, 'cells too large for', loaded, 'loaded bits')
            continue
        print(json.dumps(r), flush=True)
