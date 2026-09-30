"""Kernel cost for general nx-bit x code and ny-bit y code (integer ANF lift, low degree first)."""
import numpy as np
from logo import M

def fwht(a):
    a = np.array(a, dtype=np.int64); h = 1; n = len(a)
    while h < n:
        a = a.reshape(-1, 2 * h)
        lo = a[:, :h].copy(); hi = a[:, h:].copy()
        a[:, :h] = lo + hi; a[:, h:] = lo - hi
        a = a.reshape(-1); h *= 2
    return a

def anf_lift(ycode, xcode, ny, nx):
    nb = ny + nx; N = 1 << nb
    order = sorted(range(N), key=lambda m: (m.bit_count(), m))
    pos = {m: i for i, m in enumerate(order)}
    rows = {}
    for y in range(64):
        for x in range(64):
            w = ycode[y] | (xcode[x] << ny)
            rows.setdefault(w, set()).add(int(M[y][x]))
    piv = {}
    for w, vals in rows.items():
        if len(vals) != 1: return None
        rhs = next(iter(vals))
        # monomials m subset of w, as bitset over positions
        row = 0
        sub = w
        while True:
            row |= 1 << pos[sub]
            if sub == 0: break
            sub = (sub - 1) & w
        while row:
            i = (row & -row).bit_length() - 1
            if i in piv:
                a, b = piv[i]; row ^= a; rhs ^= b
            else:
                piv[i] = (row, rhs); break
        if not row and rhs: return None
    sol = 0
    for i in sorted(piv, reverse=True):
        row, rhs = piv[i]
        if ((row & sol).bit_count() & 1) ^ rhs: sol |= 1 << i
    return [order[i] for i in range(N) if (sol >> i) & 1], nb

def masks(terms, nb):
    N = 1 << nb
    table = np.zeros(N, dtype=np.int64)
    for m in terms:
        # add 1 to all supersets of m
        comp = (N - 1) & ~m
        sub = comp
        while True:
            table[m | sub] += 1
            if sub == 0: break
            sub = (sub - 1) & comp
    co = fwht(table)
    # phase pi*table; parity angle = -2*pi*co/N ; nonzero mod 2pi iff co % N != 0
    return int(np.count_nonzero(co[1:] % N))

def cost(ycode, xcode, ny, nx):
    r = anf_lift(ycode, xcode, ny, nx)
    if r is None: return None
    t, nb = r
    return masks(t, nb), len(t)
