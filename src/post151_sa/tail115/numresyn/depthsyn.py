"""depthsyn.py t0 q0,q1,q2 L [maxseq] : depth-aware numerical resynthesis of one convex 3q block.
Enumerates CX sequences of length L, keeps exact instantiations, greedily sparsifies the 1q slots
(none / rz / rx / u3), substitutes into the 115 circuit and tests MILP depth 114 (and 115 with CX count)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, os, json, itertools, numpy as np
from scipy.optimize import minimize, least_squares
import blockscan as BS
import resub as R
from postopt import parse_ops, fuse, write, depth, resched
from canc import simplify
import smilp

QASM = f'{WK}/kp/cx569_a33_m115.qasm'
t0 = int(sys.argv[1]); Q = [int(x) for x in sys.argv[2].split(',')]; L = int(sys.argv[3])
maxseq = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
mops = parse_ops(QASM); bops = BS.parse(QASM); n = len(mops)
B = json.load(open(f'{WK}/convex3.json'))
blk = [b for b in B if b['t0'] == t0 and b['q'] == Q][0]
idx = {q: k for k, q in enumerate(Q)}; U = np.eye(8, dtype=complex)
for i in blk['g']:
    o = mops[i]; U = (R.emb1(o[2], idx[o[1][0]]) if o[0] == 'u3' else R.CXM[(idx[o[1][0]], idx[o[1][1]])]) @ U

def rz(a): return np.diag([np.exp(-0.5j * a), np.exp(0.5j * a)])
def rx(a): return np.array([[np.cos(a / 2), -1j * np.sin(a / 2)], [-1j * np.sin(a / 2), np.cos(a / 2)]])
NP = {'n': 0, 'z': 1, 'x': 1, 'u': 3}
def gate(kind, p):
    if kind == 'n': return np.eye(2)
    if kind == 'z': return rz(p[0])
    if kind == 'x': return rx(p[0])
    return BS.u3(*p)

def slots(seq):  # slot list: (position, local wire)
    s = [(-1, q) for q in range(3)]
    for j, (c, t) in enumerate(seq): s += [(j, c), (j, t)]
    return s

def buildV(seq, kinds, p):
    V = np.eye(8, dtype=complex); k = 0; sl = slots(seq); si = 0
    for q in range(3):
        m = NP[kinds[si]]; V = R.emb1(gate(kinds[si], p[k:k + m]), q) @ V; k += m; si += 1
    for c, t in seq:
        V = R.CXM[(c, t)] @ V
        for q in (c, t):
            m = NP[kinds[si]]; V = R.emb1(gate(kinds[si], p[k:k + m]), q) @ V; k += m; si += 1
    return V

def fit(seq, kinds, starts=6, rng=np.random.default_rng(0)):
    npar = sum(NP[k] for k in kinds)
    f = lambda p: 1 - abs(np.trace(buildV(seq, kinds, p).conj().T @ U)) / 8
    for _ in range(starts):
        x0 = rng.uniform(0, 2 * np.pi, npar)
        r = minimize(f, x0, method='BFGS', options=dict(gtol=1e-12, maxiter=3000)) if npar else None
        if npar == 0:
            return (np.array([]), 0.0) if f(np.array([])) < 1e-13 else (None, None)
        if r.fun < 1e-8:
            p0 = np.append(r.x, np.angle(np.trace(U.conj().T @ buildV(seq, kinds, r.x))))
            def res(q):
                D = buildV(seq, kinds, q[:-1]) - np.exp(1j * q[-1]) * U
                return np.concatenate([D.real.ravel(), D.imag.ravel()])
            ls = least_squares(res, p0, xtol=1e-15, ftol=1e-15, gtol=1e-15, method='lm')
            err = np.max(abs(buildV(seq, kinds, ls.x[:-1]) - np.exp(1j * ls.x[-1]) * U))
            if err < 1e-13: return ls.x[:-1], err
    return None, None

def sparsify(seq):
    kinds = ['u'] * len(slots(seq)); p, e = fit(seq, kinds)
    if p is None: return None
    # inner slots first (they cost depth), then outer
    order = list(range(3, len(kinds))) + [0, 1, 2]
    for s in order:
        for alt in ('n', 'z', 'x'):
            if alt == 'z' and False: pass
            k2 = list(kinds); k2[s] = alt; p2, e2 = fit(seq, k2, starts=4)
            if p2 is not None: kinds, p = k2, p2; break
    return kinds, p

anc = [0] * n; last = [None] * 18; pred = [[] for _ in range(n)]
for i, o in enumerate(bops):
    for w in o[1]:
        if last[w] is not None: pred[i].append(last[w])
        last[w] = i
for i in range(n):
    m = 0
    for j in pred[i]: m |= (1 << j) | anc[j]
    anc[i] = m
am = 0
for i in blk['g']: am |= anc[i]
G = set(blk['g'])

def evaluate(seq, kinds, p):
    new = []; k = 0; si = 0
    for q in range(3):
        m = NP[kinds[si]]
        if kinds[si] != 'n': new.append(('u3', (Q[q],), gate(kinds[si], p[k:k + m])))
        k += m; si += 1
    for c, t in seq:
        new.append(('cx', (Q[c], Q[t]), None))
        for q in (c, t):
            m = NP[kinds[si]]
            if kinds[si] != 'n': new.append(('u3', (Q[q],), gate(kinds[si], p[k:k + m])))
            k += m; si += 1
    ops = [mops[i] for i in range(n) if i not in G and (am >> i) & 1] + new + [mops[i] for i in range(n) if i not in G and not (am >> i) & 1]
    ops = fuse(simplify(fuse(ops), verbose=False))
    return ops

pairs = [(c, t) for c in range(3) for t in range(3) if c != t]
tried = 0; results = []
for seq in itertools.product(pairs, repeat=L):
    if any(seq[j] == seq[j + 1] for j in range(L - 1)): continue
    p, e = fit(seq, ['u'] * len(slots(seq)), starts=3)
    if p is None: continue
    sp = sparsify(seq)
    if sp is None: continue
    kinds, p = sp
    ops = evaluate(seq, kinds, p)
    cx = sum(o[0] == 'cx' for o in ops); d0 = depth(ops)
    _, dr = resched(ops, trials=60, rounds=2)
    print('seq', seq, 'kinds', ''.join(kinds), 'cx', cx, 'asap', d0, 'resched', dr, flush=True)
    results.append((dr, cx, seq, kinds))
    tried += 1
    if dr <= 116:
        for TT in (114, 115):
            sol = smilp.solve(ops, TT, tlim=600, verbose=False)
            print('   MILP', TT, sol is not None, flush=True)
            if sol is not None:
                path = f'{WK}/rs/ds_{t0}_{"".join(map(str, Q))}_{tried}_d{TT}.qasm'
                write(fuse(sol), path); print('   wrote', path, 'cx', sum(o[0] == 'cx' for o in sol), flush=True); break
    if tried >= maxseq: break
print('done', sorted(results)[:5])
