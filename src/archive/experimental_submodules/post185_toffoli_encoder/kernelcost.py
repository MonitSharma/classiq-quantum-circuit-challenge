"""Kernel phase-polynomial cost for arbitrary 4-bit x/y codes (integer ANF lift)."""
import numpy as np
from logo import M
ORDER = sorted(range(256), key=lambda m: (m.bit_count(), m))
EVAL = [sum(1 << i for i, m in enumerate(ORDER) if m & ~w == 0) for w in range(256)]
H256 = np.array([[(-1) ** bin(a & b).count('1') for b in range(256)] for a in range(256)])

def anf_solution(ycode, xcode, weight=None):
    """Kernel word w = ycode | xcode<<4. Returns ANF monomial set (low degree preferred)."""
    rows = {}
    for y in range(64):
        for x in range(64):
            w = ycode[y] | (xcode[x] << 4)
            rows.setdefault(w, set()).add(int(M[y][x]))
    piv = {}
    for w, vals in rows.items():
        if len(vals) != 1:
            return None  # code does not separate
        rhs = vals.pop(); row = EVAL[w]
        while row:
            i = (row & -row).bit_length() - 1
            if i in piv:
                a, b = piv[i]; row ^= a; rhs ^= b
            else:
                piv[i] = (row, rhs); break
        if not row and rhs:
            return None
    sol = 0
    for i in sorted(piv, reverse=True):
        row, rhs = piv[i]
        if ((row & sol).bit_count() & 1) ^ rhs:
            sol |= 1 << i
    return [m for i, m in enumerate(ORDER) if sol >> i & 1]

def kernel_masks(terms):
    table = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], int)
    co = table @ H256
    return int(np.count_nonzero(co[1:]))

def cost(ycode, xcode):
    t = anf_solution(ycode, xcode)
    if t is None: return None
    return kernel_masks(t), t
