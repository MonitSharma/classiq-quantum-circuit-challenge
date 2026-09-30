"""dsloop.py in.qasm tag [k] [maxrounds] : iterated depth-aware numerical resynthesis.
Each round: convex k-qubit blocks in the commutation DAG with >=3 CX; for each, try every CX sequence with fewer CX,
exact instantiation (BFGS then Levenberg-Marquardt to 1e-13), greedy 1q-slot sparsification (none/rz/rx/u3),
substitution, rescheduling, exact MILP at depth 114 and 115. Accept exhaustively verified improvements and repeat."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, os, json, itertools, time, numpy as np
from scipy.optimize import minimize, least_squares
from postopt import parse_ops, fuse, write, depth, resched
from canc import simplify
import smilp, everify
from cblocks import Circ, gate_mat
import blockscan as BS

K = int(sys.argv[3]) if len(sys.argv) > 3 else 3
MAXR = int(sys.argv[4]) if len(sys.argv) > 4 else 20
NP = {'n': 0, 'z': 1, 'x': 1, 'u': 3}
def rz(a): return np.diag([np.exp(-0.5j * a), np.exp(0.5j * a)])
def rx(a): return np.array([[np.cos(a / 2), -1j * np.sin(a / 2)], [-1j * np.sin(a / 2), np.cos(a / 2)]])
def g1(kind, p):
    return np.eye(2) if kind == 'n' else rz(p[0]) if kind == 'z' else rx(p[0]) if kind == 'x' else BS.u3(*p)
def emb(m, p, k): return np.kron(np.kron(np.eye(1 << p), m), np.eye(1 << (k - 1 - p)))
CXC = {}
def cxm(c, t, k):
    if (c, t, k) not in CXC: CXC[c, t, k] = gate_mat(('cx', (c, t), None), {i: i for i in range(k)}, k)
    return CXC[c, t, k]
def nslots(seq, k): return k + 2 * len(seq)
def buildV(seq, kinds, p, k):
    V = np.eye(1 << k, dtype=complex); j = 0; s = 0
    for q in range(k):
        V = emb(g1(kinds[s], p[j:j + NP[kinds[s]]]), q, k) @ V; j += NP[kinds[s]]; s += 1
    for c, t in seq:
        V = cxm(c, t, k) @ V
        for q in (c, t):
            V = emb(g1(kinds[s], p[j:j + NP[kinds[s]]]), q, k) @ V; j += NP[kinds[s]]; s += 1
    return V
def fit(U, seq, kinds, k, starts=4, rng=np.random.default_rng(0)):
    npar = sum(NP[x] for x in kinds); D = 1 << k
    if npar == 0:
        V = buildV(seq, kinds, [], k); ph = np.trace(U.conj().T @ V); ph /= abs(ph) if abs(ph) > 0 else 1
        return (np.array([]), 0.0) if np.max(abs(V - ph * U)) < 1e-12 else (None, None)
    f = lambda p: 1 - abs(np.trace(buildV(seq, kinds, p, k).conj().T @ U)) / D
    for _ in range(starts):
        r = minimize(f, rng.uniform(0, 2 * np.pi, npar), method='BFGS', options=dict(gtol=1e-12, maxiter=3000))
        if r.fun < 1e-8:
            p0 = np.append(r.x, np.angle(np.trace(U.conj().T @ buildV(seq, kinds, r.x, k))))
            def res(q):
                Dm = buildV(seq, kinds, q[:-1], k) - np.exp(1j * q[-1]) * U
                return np.concatenate([Dm.real.ravel(), Dm.imag.ravel()])
            ls = least_squares(res, p0, xtol=1e-15, ftol=1e-15, gtol=1e-15, method='lm')
            err = np.max(abs(buildV(seq, kinds, ls.x[:-1], k) - np.exp(1j * ls.x[-1]) * U))
            if err < 1e-13: return ls.x[:-1], err
    return None, None
from fastfit import fit as _ffit
def fit(U, seq, kinds, k, starts=4, rng=None): return _ffit(U, seq, kinds, k, starts=starts)
def sparsify(U, seq, k):
    kinds = ['u'] * nslots(seq, k); p, e = fit(U, seq, kinds, k)
    if p is None: return None
    for s in list(range(k, len(kinds))) + list(range(k)):
        for alt in ('n', 'z', 'x'):
            k2 = list(kinds); k2[s] = alt; p2, _ = fit(U, seq, k2, k, starts=3)
            if p2 is not None: kinds, p = k2, p2; break
    return kinds, p
def gates(Q, seq, kinds, p, k):
    new = []; j = 0; s = 0
    for q in range(k):
        if kinds[s] != 'n': new.append(('u3', (Q[q],), g1(kinds[s], p[j:j + NP[kinds[s]]])))
        j += NP[kinds[s]]; s += 1
    for c, t in seq:
        new.append(('cx', (Q[c], Q[t]), None))
        for q in (c, t):
            if kinds[s] != 'n': new.append(('u3', (Q[q],), g1(kinds[s], p[j:j + NP[kinds[s]]])))
            j += NP[kinds[s]]; s += 1
    return new

def try_block(C, blk, T0, cx0, tag, log):
    Q = blk['q']; k = len(Q); U = C.unitary(blk); pairs = [(a, b) for a in range(k) for b in range(k) if a != b]
    hits = []
    for L in range(blk['ncx'] - 1, 0, -1):
        anyfit = False
        for seq in itertools.product(pairs, repeat=L):
            if any(seq[j] == seq[j + 1] for j in range(L - 1)): continue
            p, _ = fit(U, seq, ['u'] * nslots(seq, k), k, starts=3)
            if p is None: continue
            anyfit = True
            sp = sparsify(U, seq, k)
            if sp is None: continue
            kinds, p = sp
            ops = fuse(simplify(fuse(C.substitute(blk, gates(Q, seq, kinds, p, k))), verbose=False))
            cx = sum(o[0] == 'cx' for o in ops); _, dr = resched(ops, trials=60, rounds=2)
            log(f'  {Q} L{L} seq {seq} kinds {"".join(kinds)} cx {cx} resched {dr}')
            hits.append(dr)
            if len(hits) >= 6 and min(hits) >= T0 + 2: log('  abandon block (all hits too deep)'); return None
            if dr > T0 + 1: continue
            for TT in (T0 - 1, T0):
                sol = smilp.solve(ops, TT, tlim=600, verbose=False)
                log(f'    MILP {TT} {sol is not None}')
                if sol is not None:
                    sol = fuse(sol); ncx = sum(o[0] == 'cx' for o in sol)
                    if TT < T0 or ncx < cx0:
                        path = f'{WK}/rs/{tag}_d{TT}_cx{ncx}.qasm'; write(sol, path)
                        r = everify.exhaustive_verify(path, write_report=False)
                        log(f'    VERIFIED depth {r["depth"]} cx {r["cx_count"]} err {r["max_error"]:.2e} -> {path}')
                        if r['depth'] <= T0 and (r['depth'] < T0 or r['cx_count'] < cx0): return path, r['depth'], r['cx_count']
                    break
        if not anyfit: break
    return None

if __name__ == '__main__':
    cur, tag = sys.argv[1], sys.argv[2]
    logf = open(f'{WK}/rs/{tag}.log', 'a')
    def log(s): print(s, flush=True); logf.write(s + '\n'); logf.flush()
    ops = fuse(parse_ops(cur)); T0 = depth(ops); cx0 = sum(o[0] == 'cx' for o in ops)
    tried = set()
    for rnd in range(MAXR):
        C = Circ(ops, wire=os.environ.get('WIRE') == '1'); B = C.blocks(K, 3)
        log(f'round {rnd} depth {T0} cx {cx0} blocks>=3cx {len(B)} hist {sorted({b["ncx"] for b in B})}')
        hit = None
        if os.environ.get('ORDER') == 'rev': B = B[::-1]
        from collections import Counter
        twins = Counter((tuple(b['q']), tuple(sorted((o[0],) + tuple(o[1]) for o in (C.ops[i] for i in b['g'])))) for b in B)
        if os.environ.get('TWINS') == '1': log(f'twin blocks {sum(v for v in twins.values() if v > 1)}')
        SH = [int(x) for x in os.environ.get('SHARD', '0/1').split('/')]
        for bi, b in enumerate(B):
            if bi % SH[1] != SH[0]: continue
            key = (tuple(b['q']), tuple(sorted((o[0],) + tuple(o[1]) for o in (C.ops[i] for i in b['g']))))
            if os.environ.get('TWINS') == '1':
                if twins[key] < 2 or (rnd, tuple(b['g'])) in tried: continue
                tried.add((rnd, tuple(b['g'])))
            else:
                if key in tried: continue
                tried.add(key)
            log(f' block {b["q"]} cx {b["ncx"]} gates {len(b["g"])}')
            hit = try_block(C, b, T0, cx0, f'{tag}_r{rnd}', log)
            if hit: break
        if not hit: log('no further improvement'); break
        cur, T0, cx0 = hit; ops = fuse(parse_ops(cur)); log(f'accepted {cur}')
