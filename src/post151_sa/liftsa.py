"""Minimum-weight integer lift, searched properly.

feasible(S): is there an integer a supported on S with (H a)_v == 64 L(v) (mod 128)?
That is a linear system over Z/2^7; solved by valuation-ordered elimination in numpy.
Search: greedy elimination + swap moves (remove one, add one) to escape local optima,
with restarts.  Works for a general atom dictionary, so it also covers the conditional
targets where the atoms are characters AND Lambda-modulated characters.
"""
import numpy as np, random, sys, time
MOD = 128
BITS = 7

def consistent(Acols, b, mod=MOD):
    """Acols: (m, k) int array (columns = chosen atoms).  b: (m,) ints.
    True iff A x == b (mod 2^BITS) has a solution."""
    A = Acols.astype(np.int64) % mod
    bb = b.astype(np.int64) % mod
    m, k = A.shape
    r = 0
    for c in range(k):
        if r >= m: break
        col = A[r:, c]
        nz = np.nonzero(col)[0]
        if nz.size == 0: continue
        vals = col[nz]
        v2 = np.array([int(x & -x).bit_length() - 1 for x in vals])
        j = nz[np.argmin(v2)]; v = int(v2.min())
        if j != 0:
            A[[r, r + j]] = A[[r + j, r]]; bb[r], bb[r + j] = bb[r + j], bb[r]
        pv = int(A[r, c]); unit = pv >> v; inv = pow(unit, -1, mod)
        rows = np.arange(m) != r
        x = A[:, c].copy(); x[r] = 0
        xv = np.zeros(m, dtype=np.int64)
        nzr = np.nonzero(x)[0]
        for i in nzr:
            xi = int(x[i]); xv[i] = (xi & -xi).bit_length() - 1
        use = nzr[xv[nzr] >= v]
        if use.size:
            f = ((x[use] >> v) * inv) % mod
            A[use] = (A[use] - f[:, None] * A[r]) % mod
            bb[use] = (bb[use] - f * bb[r]) % mod
        r += 1
    # remaining rows must be consistent
    for i in range(m):
        if not A[i].any():
            if bb[i] % mod: return False
    # back-substitute to confirm divisibility
    piv = []
    rr = 0
    for c in range(k):
        if rr < m and A[rr, c] % mod:
            piv.append((rr, c)); rr += 1
    x = np.zeros(k, dtype=np.int64)
    for (row, c) in reversed(piv):
        s = (bb[row] - int(A[row, c + 1:] @ x[c + 1:])) % mod
        pv = int(A[row, c]); v = (pv & -pv).bit_length() - 1
        if s % (1 << v): return False
        mm = mod >> v
        x[c] = ((s >> v) * pow((pv >> v) % mm, -1, mm)) % mm if mm > 1 else 0
    resid = (A @ x - bb) % mod
    return not resid.any()

def search(Hcols, b, S0, rng, iters=4000, verbose=False):
    """Hcols: (64, D) dictionary.  Returns the smallest feasible support found."""
    D = Hcols.shape[1]
    S = list(S0)
    def feas(T): return consistent(Hcols[:, T], b)
    # greedy elimination
    改 = True
    while 改:
        改 = False
        order = S[:]; rng.shuffle(order)
        for s in order:
            T = [t for t in S if t != s]
            if T and feas(T): S = T; 改 = True
    best = S[:]
    cur = S[:]
    for it in range(iters):
        out = rng.choice(cur)
        cand = [t for t in range(D) if t not in cur]
        inn = rng.choice(cand) if cand else None
        T = [t for t in cur if t != out] + ([inn] if inn is not None else [])
        if not feas(T): continue
        cur = T
        改 = True
        while 改:
            改 = False
            order = cur[:]; rng.shuffle(order)
            for s in order:
                U = [t for t in cur if t != s]
                if U and feas(U): cur = U; 改 = True
        if len(cur) < len(best):
            best = cur[:]
            if verbose: print('   it', it, 'support', len(best), flush=True)
        if len(cur) > len(best) + 3:
            cur = best[:]
    return best
