"""Counterexample-guided exact SAT for one axis encoder on 9 physical wires.

Model: layers 'C' (disjoint CX) and 'R' (disjoint Toffolis, optional control
negation), wires 0-5 data, 6-8 clean. Endpoint: four distinct wires equal the
protected code bits (parity, label0..2) up to a per-bit complement, so the
protected integer-lifted kernel is reused unchanged. Point semantics are added
incrementally only for inputs that violate the current solution.
"""
import argparse, itertools, json, time, random
from pysat.formula import IDPool
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver
import two_stage_oracle as ts
from post258_two_stage_anf import decode

W = 9

def protected_bits(side):
    rec = json.load(open('artifacts/218/class_codes.json'))
    mask, cls, key = (32, ts.ROWCLS, 'ylab') if side == 'y' else (48, ts.COLCLS, 'xlab')
    lab = decode(rec[key])
    out = []
    for v, c in enumerate(cls):
        p = (v & mask).bit_count() % 2
        L = lab[(p, c)]
        out.append((p, L & 1, (L >> 1) & 1, (L >> 2) & 1))
    return out

class Model:
    def __init__(self, pattern, target, solver, free=False, cells=None):
        self.pattern, self.target, self.free, self.cells = pattern, target, free, cells
        self.pool = IDPool(); self.s = Solver(name=solver)
        self.points = set(); self.V = lambda *k: self.pool.id(k)
        self.structure()

    def add(self, c): self.s.add_clause(c)

    def structure(self):
        V, add = self.V, self.add
        amo = lambda lits: [add([-a, -b]) for a, b in itertools.combinations(lits, 2)]
        for l, kind in enumerate(self.pattern):
            if kind == 'C':
                for t in range(W): amo([V('c', l, t, c) for c in range(W) if c != t])
                for c in range(W):
                    amo([V('c', l, t, c) for t in range(W) if t != c])
                    for t in range(W):
                        if t == c: continue
                        for u in range(W):
                            if u != t: add([-V('c', l, t, c), -V('c', l, u, t)])
                # symmetry: forbid CX(c,t) immediately repeated from previous C layer
                if l > 0 and self.pattern[l - 1] == 'C':
                    for t in range(W):
                        for c in range(W):
                            if c != t: add([-V('c', l, t, c), -V('c', l - 1, t, c)])
            else:
                for t in range(W):
                    sa = [V('ra', l, t, a) for a in range(W) if a != t]
                    sb = [V('rb', l, t, b) for b in range(W) if b != t]
                    amo(sa); amo(sb)
                    on = V('ron', l, t)
                    add([-on] + sa); add([-on] + sb)
                    for x in sa + sb: add([on, -x])
                    for a in range(W):
                        if a == t: continue
                        add([-V('ra', l, t, a), -V('rb', l, t, a)])
                        for b in range(a):
                            if b != t: add([-V('ra', l, t, a), -V('rb', l, t, b)])
                for w in range(W):
                    roles = [V('ron', l, w)] + [V(tag, l, t, w) for t in range(W) if t != w for tag in ('ra', 'rb')]
                    amo(roles)
        sel = [[V('sel', j, w) for w in range(W)] for j in range(4)]
        for j in range(4):
            add(sel[j]); amo(sel[j])
        for w in range(W): amo([sel[j][w] for j in range(4)])
        # symmetry: ancilla wires 6,7,8 are interchangeable until first used
        if self.free:
            keys = sorted(set(self.cells))
            for par in (0, 1):
                ks = [k for k in keys if k[0] == par]
                for a, b in itertools.combinations(ks, 2):
                    # labels of different classes in one parity differ in some bit
                    diff = []
                    for j in range(3):
                        d = V('ld', a, b, j); diff.append(d)
                        la, lb = V('lab', a, j), V('lab', b, j)
                        add([-d, la, lb]); add([-d, -la, -lb])
                    add(diff)

    def add_point(self, p):
        if p in self.points: return
        self.points.add(p)
        V, add = self.V, self.add
        val = lambda l, w: V('v', l, w, p)
        def xor3(z, a, b): add([-z, a, b]); add([-z, -a, -b]); add([z, -a, b]); add([z, a, -b])
        for w in range(W):
            add([val(0, w)] if (w < 6 and (p >> w) & 1) else [-val(0, w)])
        for l, kind in enumerate(self.pattern):
            if kind == 'C':
                for t in range(W):
                    cv = V('cv', l, t, p); sels = []
                    for c in range(W):
                        if c == t: continue
                        s = V('c', l, t, c); sels.append(s)
                        add([-s, -val(l, c), cv]); add([-s, val(l, c), -cv])
                    add(sels + [-cv])
                    xor3(val(l + 1, t), val(l, t), cv)
            else:
                for t in range(W):
                    A, B, P = V('A', l, t, p), V('B', l, t, p), V('P', l, t, p)
                    for tag, var in (('ra', A), ('rb', B)):
                        sels = []
                        for c in range(W):
                            if c == t: continue
                            s = V(tag, l, t, c); sels.append(s)
                            add([-s, -val(l, c), var]); add([-s, val(l, c), -var])
                        sels.append(-V('ron', l, t))
                        add(sels + [-var])
                    A2, B2 = V('A2', l, t, p), V('B2', l, t, p)
                    xor3(A2, A, V('na', l, t)); xor3(B2, B, V('nb', l, t))
                    on = V('ron', l, t)
                    add([-P, A2]); add([-P, B2]); add([-P, on]); add([P, -A2, -B2, -on])
                    xor3(val(l + 1, t), val(l, t), P)
        L = len(self.pattern)
        for j in range(4):
            if self.free and j > 0:
                lab = V('lab', self.cells[p], j - 1)
                for w in range(W):
                    s_ = V('sel', j, w)
                    add([-s_, -val(L, w), lab]); add([-s_, val(L, w), -lab])
                continue
            bit = self.target[p][j]
            for w in range(W):
                s, pol = V('sel', j, w), V('pol', j)
                # val(L,w) == bit xor pol
                if bit:
                    add([-s, val(L, w), pol]); add([-s, -val(L, w), -pol])
                else:
                    add([-s, -val(L, w), pol]); add([-s, val(L, w), -pol])

    def solution(self):
        m = set(l for l in self.s.get_model() if l > 0)
        has = lambda *k: k in self.pool.obj2id and self.pool.obj2id[k] in m
        ops = []
        for l, kind in enumerate(self.pattern):
            layer = []
            for t in range(W):
                if kind == 'C':
                    for c in range(W):
                        if c != t and has('c', l, t, c): layer.append(['cx', c, t])
                elif has('ron', l, t):
                    a = next(c for c in range(W) if c != t and has('ra', l, t, c))
                    b = next(c for c in range(W) if c != t and has('rb', l, t, c))
                    layer.append(['ccx', a, b, t, int(has('na', l, t)), int(has('nb', l, t))])
            ops.append(layer)
        code = [next(w for w in range(W) if has('sel', j, w)) for j in range(4)]
        pol = [int(has('pol', j)) for j in range(4)]
        if self.free:
            pol = [pol[0], 0, 0, 0]
            labels = {k: sum(int(has('lab', k, j)) << j for j in range(3)) for k in set(self.cells)}
            self.target = [(self.target[p][0],) + tuple((labels[self.cells[p]] >> j) & 1 for j in range(3)) for p in range(64)]
            self.labels = labels
        return ops, code, pol

def simulate(ops, p):
    s = [(p >> w) & 1 if w < 6 else 0 for w in range(W)]
    for layer in ops:
        new = list(s)
        for op in layer:
            if op[0] == 'cx': new[op[2]] ^= s[op[1]]
            else: new[op[3]] ^= (s[op[1]] ^ op[4]) & (s[op[2]] ^ op[5])
        s = new
    return s

def cells_of(side):
    mask, cls = (32, ts.ROWCLS) if side == 'y' else (48, ts.COLCLS)
    return [((v & mask).bit_count() % 2, c) for v, c in enumerate(cls)]

def run(side, pattern, solver, seed, deadline, free=False):
    target = protected_bits(side)
    M = Model(pattern, target, solver, free=free, cells=cells_of(side))
    rng = random.Random(seed)
    for p in rng.sample(range(64), 6): M.add_point(p)
    t0 = time.time(); it = 0
    while True:
        it += 1
        if not M.s.solve():
            print('RESULT UNSAT', side, pattern, 'points', len(M.points), 'iters', it, 'secs', round(time.time() - t0, 1), flush=True)
            return None
        ops, code, pol = M.solution()
        target = M.target
        bad = [p for p in range(64)
               if tuple(simulate(ops, p)[code[j]] ^ pol[j] for j in range(4)) != target[p]]
        print(f'iter {it} points {len(M.points)} violations {len(bad)} secs {time.time()-t0:.1f}', flush=True)
        if not bad:
            print('RESULT SAT', side, pattern, 'points', len(M.points), 'secs', round(time.time() - t0, 1), flush=True)
            out = dict(side=side, pattern=pattern, ops=ops, code=code, pol=pol, free=free)
            if free: out['labels'] = {f'{k[0]},{k[1]}': v for k, v in M.labels.items()}
            return out
        for p in rng.sample(bad, min(3, len(bad))): M.add_point(p)
        if time.time() - t0 > deadline:
            print('RESULT TIMEOUT', flush=True); return None

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--side', required=True); ap.add_argument('--pattern', required=True)
    ap.add_argument('--solver', default='cadical195'); ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--deadline', type=float, default=3000); ap.add_argument('--out')
    ap.add_argument('--free', action='store_true')
    a = ap.parse_args()
    r = run(a.side, a.pattern, a.solver, a.seed, a.deadline, a.free)
    if r and a.out: json.dump(r, open(a.out, 'w'))
