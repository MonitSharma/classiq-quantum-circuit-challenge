"""Minimal-Walsh-support integer lift.

A loader target pi*L (L in {0,1}^64) may be replaced by pi*(L+2z) for any integer z:
the applied phase is unchanged mod 2pi.  With a = H(L+2z) the rotation set is supp(a),
and the admissible a are exactly those integer vectors with

        (H a)_v  ==  64 * L(v)   (mod 128)        [equivalently a in H(L + 2 Z^64)]

so minimising the loader's rotation count for that target is a minimum-weight problem
in a coset of a Z/128-module.  We solve it by greedy support elimination: repeatedly
test whether the system stays consistent after deleting one more coordinate.
"""
import numpy as np, random, sys

MOD = 128

def solve_mod(A, b, mod=MOD):
    """Solve A x == b (mod 2^k) by Gaussian elimination on 2-adic valuations.
    A: list of rows (lists of ints), b: list of ints.  Returns a solution or None."""
    m = len(A); n = len(A[0]) if m else 0
    A = [row[:] for row in A]; b = list(b)
    piv = []            # (row, col)
    r = 0
    for c in range(n):
        if r >= m: break
        # pick the row with the smallest 2-adic valuation in column c
        best = -1; bv = 99
        for i in range(r, m):
            x = A[i][c] % mod
            if x == 0: continue
            v = (x & -x).bit_length() - 1
            if v < bv: bv = v; best = i
        if best < 0: continue
        A[r], A[best] = A[best], A[r]; b[r], b[best] = b[best], b[r]
        pv = A[r][c] % mod
        v = (pv & -pv).bit_length() - 1
        unit = pv >> v
        inv = pow(unit, -1, mod)
        for i in range(m):
            if i == r: continue
            x = A[i][c] % mod
            if x == 0: continue
            xv = (x & -x).bit_length() - 1
            if xv < v:          # cannot eliminate; skip (handled by later pivots)
                continue
            f = ((x >> v) * inv) % mod
            for j in range(c, n):
                A[i][j] = (A[i][j] - f * A[r][j]) % mod
            b[i] = (b[i] - f * b[r]) % mod
        piv.append((r, c)); r += 1
    # consistency + back substitution
    x = [0] * n
    for (rr, cc) in reversed(piv):
        s = (b[rr] - sum(A[rr][j] * x[j] for j in range(cc + 1, n))) % mod
        pv = A[rr][cc] % mod
        v = (pv & -pv).bit_length() - 1
        if s % (1 << v) != 0: return None
        unit = pv >> v
        mm = mod >> v
        x[cc] = ((s >> v) * pow(unit % mm, -1, mm)) % mm if mm > 1 else 0
    for i in range(m):
        if (sum(A[i][j] * x[j] for j in range(n)) - b[i]) % mod != 0:
            # rows without pivots must be consistent
            if any(A[i][j] % mod for j in range(n)): return None
            if b[i] % mod: return None
    return x

def feasible(S, L, Hm, mod=MOD):
    A = [[int(Hm[v][s]) for s in S] for v in range(64)]
    b = [(64 * int(L[v])) % mod for v in range(64)]
    return solve_mod(A, b, mod)

def greedy(L, Hm, S0, rng, rounds=3):
    S = list(S0)
    improved = True
    while improved:
        improved = False
        order = S[:]; rng.shuffle(order)
        for s in order:
            if s not in S: continue
            T = [t for t in S if t != s]
            if feasible(T, L, Hm) is not None:
                S = T; improved = True
    return S

if __name__ == '__main__':
    sys.path.insert(0, '/work/cq/src/post151_sa')
    from codes import xcode, ycode, bits, H
    side = sys.argv[1]; comb = int(sys.argv[2]); seeds = int(sys.argv[3])
    code = xcode if side == 'x' else ycode
    B = bits(code)
    L = np.zeros(64, dtype=np.int64)
    for j in range(3):
        if comb >> j & 1: L ^= B[j]
    a0 = H @ L
    S0 = [s for s in range(64) if a0[s] != 0]
    print(f'{side} combo {comb}: base Walsh support {len(S0)}', flush=True)
    best = list(S0)
    for sd in range(seeds):
        rng = random.Random(1234 + sd)
        start = list(range(64)) if sd % 2 else list(S0)
        S = greedy(L, H, start, rng)
        if len(S) < len(best):
            best = S; print(f'  seed {sd}: support {len(S)}  {sorted(S)}', flush=True)
    print(f'BEST {side} combo {comb}: {len(best)}', flush=True)
    sol = feasible(best, L, H)
    # verify
    u = np.zeros(64)
    for k, s in enumerate(best):
        u = u + sol[k] * H[s]
    u = u / 64.0
    ok = np.all((np.round(u) - u) == 0) and np.all((np.round(u).astype(int) - L) % 2 == 0)
    print('verified integer + parity:', bool(ok))
    np.save(f'/work/cq/work/lift_{side}_{comb}.npy', np.array(sorted(best)))
