"""inst3.py : for the largest convex 3q blocks, try to instantiate every CX sequence with fewer CX
(QSearch-style template: u3 on all wires at start, u3 on both CX wires after each CX)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, json, itertools, numpy as np
from scipy.optimize import minimize
from blockscan import parse, u3

ops = parse(sys.argv[1]); B = json.load(open(f'{WK}/convex3.json'))
mincx = int(sys.argv[2]) if len(sys.argv) > 2 else 3
I2 = np.eye(2)

def emb1(m, k):  # k in 0..2, qubit 0 = most significant
    mats = [I2, I2, I2]; mats[k] = m
    return np.kron(np.kron(mats[0], mats[1]), mats[2])

CXM = {}
for c in range(3):
    for t in range(3):
        if c == t: continue
        M = np.zeros((8, 8))
        for s in range(8):
            b = [(s >> 2) & 1, (s >> 1) & 1, s & 1]
            if b[c]: b[t] ^= 1
            M[b[0] * 4 + b[1] * 2 + b[2], s] = 1
        CXM[(c, t)] = M

def block_U(blk):
    Q = blk['q']; idx = {q: k for k, q in enumerate(Q)}; U = np.eye(8, dtype=complex)
    for i in blk['g']:
        o = ops[i]
        if o[0] == 'u3': G = emb1(u3(*o[2]), idx[o[1][0]])
        else: G = CXM[(idx[o[1][0]], idx[o[1][1]])]
        U = G @ U
    return U

def build(seq, p):
    V = np.eye(8, dtype=complex); k = 0
    for q in range(3): V = emb1(u3(*p[k:k + 3]), q) @ V; k += 3
    for c, t in seq:
        V = CXM[(c, t)] @ V
        for q in (c, t): V = emb1(u3(*p[k:k + 3]), q) @ V; k += 3
    return V

def fit(U, seq, starts=8, rng=np.random.default_rng(0)):
    npar = 9 + 6 * len(seq); best = 1.0
    f = lambda p: 1 - abs(np.trace(build(seq, p).conj().T @ U)) / 8
    for _ in range(starts):
        r = minimize(f, rng.uniform(0, 2 * np.pi, npar), method='BFGS', options=dict(gtol=1e-10, maxiter=2000))
        best = min(best, r.fun)
        if best < 1e-10: break
    return best

pairs = [(c, t) for c in range(3) for t in range(3) if c != t]
for blk in B:
    if blk['ncx'] < mincx: continue
    U = block_U(blk); k = blk['ncx']
    found = None
    for L in range(0, k):
        for seq in itertools.product(pairs, repeat=L):
            if any(seq[j] == seq[j + 1] for j in range(L - 1)): continue
            if L and fit(U, seq, starts=4) < 1e-9: found = (L, seq); break
        if found: break
    print(blk['q'], 't0', blk['t0'], 'cx', k, 'span', blk['span'], '->', found, flush=True)
