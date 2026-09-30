"""resub.py : substitute convex 3q blocks by fewer-CX numerically instantiated equivalents (refined to machine
precision), then fuse/simplify and test exact depth feasibility with the time-indexed MILP.
usage: python3 resub.py in.qasm out_prefix 'JSON list of [t0, [q...], [[c,t],...]]'"""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, os, json, numpy as np
from scipy.optimize import minimize, least_squares
os.chdir(PS)
import blockscan as BS
from postopt import parse_ops, fuse, write, depth
from canc import simplify
import smilp

I2 = np.eye(2)
def emb1(m, k):
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

def buildV(seq, p):
    V = np.eye(8, dtype=complex); k = 0
    for q in range(3): V = emb1(BS.u3(*p[k:k + 3]), q) @ V; k += 3
    for c, t in seq:
        V = CXM[(c, t)] @ V
        for q in (c, t): V = emb1(BS.u3(*p[k:k + 3]), q) @ V; k += 3
    return V

def exact_fit(U, seq, starts=40, seed=0):
    rng = np.random.default_rng(seed); npar = 9 + 6 * len(seq)
    f = lambda p: 1 - abs(np.trace(buildV(seq, p).conj().T @ U)) / 8
    for _ in range(starts):
        r = minimize(f, rng.uniform(0, 2 * np.pi, npar), method='BFGS', options=dict(gtol=1e-12, maxiter=4000))
        if r.fun < 1e-8:
            p0 = np.append(r.x, np.angle(np.trace(U.conj().T @ buildV(seq, r.x))))
            res = lambda q: np.concatenate([(buildV(seq, q[:-1]) - np.exp(1j * q[-1]) * U).real.ravel(),
                                            (buildV(seq, q[:-1]) - np.exp(1j * q[-1]) * U).imag.ravel()])
            ls = least_squares(res, p0, xtol=1e-15, ftol=1e-15, gtol=1e-15, method='lm')
            err = np.max(abs(buildV(seq, ls.x[:-1]) - np.exp(1j * ls.x[-1]) * U))
            if err < 1e-13: return ls.x[:-1], err
    return None, None

def substitute(qasm, subs):
    bops = BS.parse(qasm); mops = parse_ops(qasm); assert len(bops) == len(mops)
    B = json.load(open(f'{WK}/convex3.json'))
    n = len(mops)
    # DAG ancestors (wire order)
    last = [None] * 18; pred = [[] for _ in range(n)]
    for i, o in enumerate(bops):
        for q in o[1]:
            if last[q] is not None: pred[i].append(last[q])
            last[q] = i
    anc = [0] * n
    for i in range(n):
        m = 0
        for j in pred[i]: m |= (1 << j) | anc[j]
        anc[i] = m
    order = list(range(n)); newops = {i: mops[i] for i in range(n)}; groups = []
    for t0, Q, seq in subs:
        blk = [b for b in B if b['t0'] == t0 and b['q'] == Q][0]
        # block unitary from the matrix ops
        idx = {q: k for k, q in enumerate(Q)}; U = np.eye(8, dtype=complex)
        for i in blk['g']:
            o = mops[i]
            G = emb1(o[2], idx[o[1][0]]) if o[0] == 'u3' else CXM[(idx[o[1][0]], idx[o[1][1]])]
            U = G @ U
        p, err = exact_fit(U, [tuple(s) for s in seq])
        print('block', Q, t0, 'seq', seq, 'fit err', err, flush=True)
        if p is None: return None
        new = []; k = 0
        for q in range(3): new.append(('u3', (Q[q],), BS.u3(*p[k:k + 3]))); k += 3
        for c, t in seq:
            new.append(('cx', (Q[c], Q[t]), None))
            for q in (c, t): new.append(('u3', (Q[q],), BS.u3(*p[k:k + 3]))); k += 3
        groups.append((frozenset(blk['g']), new))
    # rebuild order: repeatedly place block as a unit at the position of its first gate after moving its ancestors ahead
    seqops = [('g', i) for i in range(n)]
    for gset, new in groups:
        am = 0
        for i in gset: am |= anc[i]
        isanc = lambda x: ((am >> x[1]) & 1) if x[0] == 'g' else any((am >> j) & 1 for j in x[2])
        inblk = lambda x: x[0] == 'g' and x[1] in gset
        pre = [x for x in seqops if not inblk(x) and isanc(x)]
        rest = [x for x in seqops if not inblk(x) and not isanc(x)]
        seqops = pre + [('n', new, gset)] + rest
    out = []
    for x in seqops:
        if x[0] == 'g': out.append(mops[x[1]])
        else: out += x[1]
    return out

if __name__ == '__main__':
    qasm, pref = sys.argv[1], sys.argv[2]; subs = json.loads(sys.argv[3])
    ops = substitute(qasm, subs)
    ops = fuse(simplify(fuse(ops), verbose=False))
    print('after subst: cx', sum(o[0] == 'cx' for o in ops), 'asap depth', depth(ops), flush=True)
    for TT in (114, 115):
        sol = smilp.solve(ops, TT, tlim=600, verbose=False)
        print('MILP', TT, sol is not None, flush=True)
        if sol is not None:
            path = f'{pref}_d{TT}.qasm'; write(fuse(sol), path); print('wrote', path, 'depth', depth(fuse(sol)), 'cx', sum(o[0] == 'cx' for o in sol)); break
