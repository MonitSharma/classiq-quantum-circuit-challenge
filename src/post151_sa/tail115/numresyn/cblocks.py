"""cblocks.py : convex k-qubit blocks in the COMMUTATION DAG (cdag.build) of a fused u3/cx circuit,
plus helpers to compute block unitaries and to substitute a block with a new gate list."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, itertools, numpy as np
from postopt import parse_ops, fuse
from cdag import build

class Circ:
    def __init__(self, ops, wire=False):
        self.ops = ops; n = self.n = len(ops)
        if wire:
            succ = [set() for _ in range(n)]; pred = [set() for _ in range(n)]; last = [None] * 18
            for i, o in enumerate(ops):
                for q in o[1]:
                    if last[q] is not None: succ[last[q]].add(i); pred[i].add(last[q])
                    last[q] = i
        else:
            T, succ, pred = build(ops)
        self.succ = [sorted(s) for s in succ]; self.pred = [sorted(p) for p in pred]
        desc = [0] * n
        for i in range(n - 1, -1, -1):
            m = 0
            for j in self.succ[i]: m |= (1 << j) | desc[j]
            desc[i] = m
        anc = [0] * n
        for i in range(n):
            m = 0
            for j in self.pred[i]: m |= (1 << j) | anc[j]
            anc[i] = m
        self.desc, self.anc = desc, anc
        self.qmask = [sum(1 << q for q in o[1]) for o in ops]

    def closure(self, S):
        d = a = 0
        for i in bits(S): d |= self.desc[i]; a |= self.anc[i]
        return S | (d & a)

    def grow(self, seed, T):
        tm = sum(1 << q for q in T); S = 1 << seed; changed = True
        while changed:
            changed = False; nb = 0
            for i in bits(S):
                for j in self.succ[i] + self.pred[i]:
                    if not (S >> j) & 1 and (self.qmask[j] & ~tm) == 0: nb |= 1 << j
            for j in bits(nb):
                C = self.closure(S | (1 << j))
                if all((self.qmask[k] & ~tm) == 0 for k in bits(C & ~S)): S = C; changed = True
        return S

    def blocks(self, k=3, mincx=3):
        seen = {}
        for i, o in enumerate(self.ops):
            if o[0] != 'cx': continue
            others = [q for q in range(18) if q not in o[1]]
            for extra in itertools.combinations(others, k - 2):
                T = tuple(sorted(o[1] + extra)); S = self.grow(i, T)
                if S not in seen: seen[S] = T
        res = []
        for S, T in seen.items():
            g = list(bits(S)); ncx = sum(self.ops[j][0] == 'cx' for j in g)
            if ncx < mincx or len({q for j in g for q in self.ops[j][1]}) < k: continue
            res.append(dict(q=list(T), g=g, ncx=ncx))
        res.sort(key=lambda r: -r['ncx']); keep = []
        for r in res:
            s = set(r['g'])
            if any(s <= set(x['g']) for x in keep): continue
            keep.append(r)
        return keep

    def unitary(self, blk):
        Q = blk['q']; k = len(Q); idx = {q: j for j, q in enumerate(Q)}; U = np.eye(1 << k, dtype=complex)
        for i in blk['g']:
            o = self.ops[i]; U = gate_mat(o, idx, k) @ U
        return U

    def substitute(self, blk, new):
        G = set(blk['g']); am = 0
        for i in G: am |= self.anc[i]
        return [self.ops[i] for i in range(self.n) if i not in G and (am >> i) & 1] + new + \
               [self.ops[i] for i in range(self.n) if i not in G and not (am >> i) & 1]

def bits(x):
    while x:
        b = x & -x; yield b.bit_length() - 1; x ^= b

def gate_mat(o, idx, k):
    if o[0] == 'u3':
        p = idx[o[1][0]]; return np.kron(np.kron(np.eye(1 << p), o[2]), np.eye(1 << (k - 1 - p)))
    c, t = idx[o[1][0]], idx[o[1][1]]; M = np.zeros((1 << k, 1 << k))
    for s in range(1 << k):
        b = s
        if (s >> (k - 1 - c)) & 1: b ^= 1 << (k - 1 - t)
        M[b, s] = 1
    return M
