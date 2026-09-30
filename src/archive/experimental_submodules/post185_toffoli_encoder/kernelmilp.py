"""Exact minimum-support phase polynomial for an 8-bit (or general) kernel via MILP (HiGHS).
angles theta_S = a_S * pi / 2^(k-1), a_S in [0, 2^k - 1]; constraint for each reachable word w:
sum_S a_S [S.w] = 2^(k-1) F(w) + 2^k m_w."""
import sys, json, time
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix
from logo import M

def reachable(ycode, xcode, ny, nx):
    pts = {}
    for y in range(64):
        for x in range(64):
            w = ycode[y] | (xcode[x] << ny)
            v = int(M[y][x])
            if pts.setdefault(w, v) != v:
                return None
    return pts

def solve(ycode, xcode, ny=4, nx=4, k=4, time_limit=120, verbose=False):
    nb = ny + nx; N = 1 << nb; mod = 1 << k; half = mod // 2
    pts = reachable(ycode, xcode, ny, nx)
    words = sorted(pts)
    S = list(range(1, N))
    nS = len(S); nW = len(words)
    # variables: a_S (int 0..mod-1), z_S (binary), m_w (int), c (global const int 0..mod-1)
    nvar = 2 * nS + nW + 1
    A = lil_matrix((nW + nS, nvar))
    lb = np.zeros(nW + nS); ub = np.zeros(nW + nS)
    for i, w in enumerate(words):
        for j, s in enumerate(S):
            if bin(s & w).count('1') & 1:
                A[i, j] = 1
        A[i, 2 * nS + i] = -mod
        A[i, nvar - 1] = 1          # global phase offset
        lb[i] = ub[i] = half * pts[w]
    for j in range(nS):
        A[nW + j, j] = 1; A[nW + j, nS + j] = -(mod - 1)
        lb[nW + j] = -np.inf; ub[nW + j] = 0
    c = np.zeros(nvar); c[nS:2 * nS] = 1
    integrality = np.ones(nvar)
    lo = np.zeros(nvar); hi = np.zeros(nvar)
    hi[:nS] = mod - 1; hi[nS:2 * nS] = 1
    lo[2 * nS:2 * nS + nW] = -nS * mod; hi[2 * nS:2 * nS + nW] = nS * mod
    hi[nvar - 1] = mod - 1
    t0 = time.time()
    res = milp(c, constraints=LinearConstraint(csr_matrix(A), lb, ub), integrality=integrality, bounds=Bounds(lo, hi),
               options=dict(time_limit=time_limit, disp=verbose))
    a = np.round(res.x[:nS]).astype(int) % mod if res.x is not None else None
    terms = {S[j]: int(a[j]) for j in range(nS) if a is not None and a[j] % mod}
    return dict(status=res.status, message=res.message, terms=len(terms), bound=getattr(res, 'mip_dual_bound', None), seconds=round(time.time() - t0, 1)), terms

if __name__ == '__main__':
    sys.path.insert(0, 'src')
    import two_stage_oracle as ts
    from post258_two_stage_anf import decode
    rec = json.load(open('artifacts/185/class_codes.json'))
    yl, xl = decode(rec['ylab']), decode(rec['xlab'])
    ycode = [((y >> 5) & 1) | (yl[((y >> 5) & 1, ts.ROWCLS[y])] << 1) for y in range(64)]
    xcode = [(((x & 48).bit_count()) & 1) | (xl[((x & 48).bit_count() & 1, ts.COLCLS[x])] << 1) for x in range(64)]
    for k in (3, 4, 5):
        info, terms = solve(ycode, xcode, k=k, time_limit=float(sys.argv[1]) if len(sys.argv) > 1 else 120)
        print('k', k, info, flush=True)
