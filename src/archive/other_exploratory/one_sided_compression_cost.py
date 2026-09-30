"""How expensive is the phase if only ONE axis is compressed?

The protected design pays two 77-layer QROMs so that the kernel sees only
8 code wires (89 Walsh masks, 38 native layers).  This measures the opposite
trade: compress x only, leave y as raw coordinate wires, and let the phase
polynomial act on (x-descriptor, y).  The y-QROM then disappears entirely.

Reported quantity is the integer-lift Walsh mask count of the exact phase table
on the compressed variable set, which is the direct cost driver of
post218_beam_phase.psynth.  Calibration: 89 masks -> 38 native layers measured
on the protected kernel.
"""
import itertools, math, sys
sys.path.insert(0, 'src')
import numpy as np
import two_stage_oracle as ts


def anf_bits(table, n):
    a = table[:]
    for i in range(n):
        for m in range(1 << n):
            if m >> i & 1:
                a[m] ^= a[m ^ (1 << i)]
    return a


def lift_masks(table, n):
    a = anf_bits(table, n)
    terms = [m for m in range(1, 1 << n) if a[m]]
    lifted = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(1 << n)], float)
    h = 1
    while h < (1 << n):
        for i in range(0, 1 << n, 2 * h):
            lo = lifted[i:i+h].copy(); hi = lifted[i+h:i+2*h].copy()
            lifted[i:i+h] = lo + hi; lifted[i+h:i+2*h] = lo - hi
        h *= 2
    masks = int(np.sum(np.abs(lifted[1:]) > 1e-9))
    return masks, len(terms)


def label_assign(cls, mask):
    """3-bit label per (parity, class) cell, injective within each parity."""
    cells = sorted({((v & mask).bit_count() % 2, c) for v, c in enumerate(cls)})
    lab = {}
    for b in (0, 1):
        group = [c for (p, c) in cells if p == b]
        for i, c in enumerate(group):
            lab[(b, c)] = i
    return lab


def describe(side, mask):
    cls = ts.ROWCLS if side == 'y' else ts.COLCLS
    lab = label_assign(cls, mask)
    return [((v & mask).bit_count() % 2) | (lab[((v & mask).bit_count() % 2, c)] << 1)
            for v, c in enumerate(cls)]


def phase_masks(xdesc, ydesc, nx, ny):
    """Exact phase table on (xdesc, ydesc) pairs; fill unreachable with 0."""
    n = nx + ny
    tab = [0] * (1 << n)
    seen = {}
    for x in range(64):
        for y in range(64):
            w = xdesc[x] | (ydesc[y] << nx)
            b = int(ts.logo(x, y))
            if seen.setdefault(w, b) != b:
                raise AssertionError('descriptor not separating')
            tab[w] = b
    return lift_masks(tab, n), len(seen)


if __name__ == '__main__':
    xcodes = {m: describe('x', m) for m in (6, 16, 48, 60)}
    ycodes = {m: describe('y', m) for m in (32,)}
    print('calibration: protected two-sided 8-wire kernel = 89 masks / 38 layers')
    yd = list(range(64))                       # raw y on 6 wires
    for m, xd in xcodes.items():
        (mk, terms), reach = phase_masks(xd, yd, 4, 6)
        print(f'  x-desc(mask {m}, 4 bits) + raw y (6 bits): masks {mk}, anf {terms}, reachable {reach}')
    # also: raw x + raw y (no compression at all)
    (mk, terms), reach = phase_masks(list(range(64)), list(range(64)), 6, 6)
    print(f'  raw x + raw y (12 bits): masks {mk}, anf {terms}, reachable {reach}')
    # and the protected two-sided 4+4 for calibration
    for mx in (48,):
        for my in (32,):
            (mk, terms), reach = phase_masks(xcodes[mx], ycodes[my], 4, 4)
            print(f'  CALIBRATION x-desc{mx} + y-desc{my} (8 bits): masks {mk}, anf {terms}, reachable {reach}')
