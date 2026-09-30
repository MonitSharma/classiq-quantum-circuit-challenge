"""Exact SAT for one axis encoder on 9 physical wires (6 data + 3 clean ancillas).

Layers: 'C' = one CX layer (disjoint CX gates), 'R' = one batch of disjoint
(relative-phase) Toffolis with optional control negations. Endpoint: some K
wires jointly separate every pair of coordinates with different classes, i.e.
they form a class code for the kernel. Labels and networks are free.
"""
import argparse, itertools, json, sys, time
from pysat.formula import IDPool
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver

def logo(x, y):
    return ((2 <= x <= 26 and 29 <= y <= 53) or (26 <= x <= 49 and 39 <= y <= 43)
            or (x - 55) ** 2 + (y - 41) ** 2 <= 42 or (x - 40) ** 2 + (y - 19) ** 2 <= 72)

def classes():
    R = {}; ROW = [0] * 64; C = {}; COL = [0] * 64
    for y in range(64): ROW[y] = R.setdefault(tuple(int(logo(x, y)) for x in range(64)), len(R))
    for x in range(64): COL[x] = C.setdefault(tuple(int(logo(x, y)) for y in range(64)), len(C))
    return ROW, COL

W = 9; NP = 64

def build(cls, pattern, K, extra=None):
    pool = IDPool(); cl = []
    V = lambda *k: pool.id(k)
    def xor3(z, a, b):  # z = a xor b
        cl.extend([[-z, a, b], [-z, -a, -b], [z, -a, b], [z, a, -b]])
    val = lambda l, w, p: V('v', l, w, p)
    for w in range(W):
        for p in range(NP):
            bit = (p >> w) & 1 if w < 6 else 0
            cl.append([val(0, w, p)] if bit else [-val(0, w, p)])
    for l, kind in enumerate(pattern):
        if kind == 'C':
            for t in range(W):
                opts = [V('c', l, t, c) for c in range(W) if c != t]
                for a, b in itertools.combinations(opts, 2): cl.append([-a, -b])
            for c in range(W):
                # a control is used by at most one target; a target is not a control
                users = [V('c', l, t, c) for t in range(W) if t != c]
                for a, b in itertools.combinations(users, 2): cl.append([-a, -b])
                for t in range(W):
                    if t == c: continue
                    for u in range(W):
                        if u != t: cl.append([-V('c', l, t, c), -V('c', l, u, t)])
            for t in range(W):
                for p in range(NP):
                    cv = V('cv', l, t, p)
                    anysel = []
                    for c in range(W):
                        if c == t: continue
                        s = V('c', l, t, c); anysel.append(s)
                        cl.append([-s, -val(l, c, p), cv]); cl.append([-s, val(l, c, p), -cv])
                    cl.append(anysel + [-cv])
                    xor3(val(l + 1, t, p), val(l, t, p), cv)
        else:  # R
            for t in range(W):
                sa = [V('ra', l, t, a) for a in range(W) if a != t]
                sb = [V('rb', l, t, b) for b in range(W) if b != t]
                for grp in (sa, sb):
                    for a, b in itertools.combinations(grp, 2): cl.append([-a, -b])
                on = V('ron', l, t)
                cl.append([-on] + sa); cl.append([-on] + sb)
                for s in sa + sb: cl.append([on, -s])
                for a in range(W):
                    if a != t: cl.append([-V('ra', l, t, a), -V('rb', l, t, a)])
                for a in range(W):
                    for b in range(a + 1, W):  # symmetry: a < b
                        if a != t and b != t: cl.append([-V('ra', l, t, b), -V('rb', l, t, a)])
            # disjointness: each wire in at most one role across the batch
            for w in range(W):
                roles = [V('ron', l, w)]
                for t in range(W):
                    if t != w: roles += [V('ra', l, t, w), V('rb', l, t, w)]
                for a, b in itertools.combinations(roles, 2): cl.append([-a, -b])
            for t in range(W):
                na, nb = V('na', l, t), V('nb', l, t)
                for p in range(NP):
                    A, B, P = V('A', l, t, p), V('B', l, t, p), V('P', l, t, p)
                    for tag, var in (('ra', A), ('rb', B)):
                        sels = []
                        for c in range(W):
                            if c == t: continue
                            s = V(tag, l, t, c); sels.append(s)
                            cl.append([-s, -val(l, c, p), var]); cl.append([-s, val(l, c, p), -var])
                        cl.append(sels + [-var])
                    A2, B2 = V('A2', l, t, p), V('B2', l, t, p)
                    xor3(A2, A, na); xor3(B2, B, nb)
                    on = V('ron', l, t)
                    cl.extend([[-P, A2], [-P, B2], [-P, on], [P, -A2, -B2, -on]])
                    xor3(val(l + 1, t, p), val(l, t, p), P)
    L = len(pattern)
    sel = [V('sel', w) for w in range(W)]
    card = CardEnc.equals(lits=sel, bound=K, vpool=pool, encoding=EncType.seqcounter)
    cl.extend(card.clauses)
    for p in range(NP):
        for q in range(p + 1, NP):
            if cls[p] == cls[q]: continue
            ds = []
            for w in range(W):
                d = V('d', w, p, q); ds.append(d)
                cl.extend([[-d, sel[w]], [-d, val(L, w, p), val(L, w, q)], [-d, -val(L, w, p), -val(L, w, q)]])
            cl.append(ds)
    return pool, cl

def extract(model, pool, pattern):
    m = set(l for l in model if l > 0)
    has = lambda *k: pool.obj2id.get(k) in m if k in pool.obj2id else False
    ops = []
    for l, kind in enumerate(pattern):
        layer = []
        for t in range(W):
            if kind == 'C':
                for c in range(W):
                    if c != t and has('c', l, t, c): layer.append(('cx', c, t))
            else:
                if has('ron', l, t):
                    a = next(c for c in range(W) if c != t and has('ra', l, t, c))
                    b = next(c for c in range(W) if c != t and has('rb', l, t, c))
                    layer.append(('ccx', a, b, t, int(has('na', l, t)), int(has('nb', l, t))))
        ops.append(layer)
    code = [w for w in range(W) if has('sel', w)]
    return ops, code

def simulate(ops):
    out = []
    for p in range(NP):
        s = [(p >> w) & 1 if w < 6 else 0 for w in range(W)]
        for layer in ops:
            new = list(s)
            for op in layer:
                if op[0] == 'cx': new[op[2]] ^= s[op[1]]
                else: new[op[3]] ^= (s[op[1]] ^ op[4]) & (s[op[2]] ^ op[5])
            s = new
        out.append(s)
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--side', choices='xy', required=True)
    ap.add_argument('--pattern', required=True)
    ap.add_argument('--K', type=int, default=4)
    ap.add_argument('--solver', default='cadical195')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    ROW, COL = classes(); cls = COL if a.side == 'x' else ROW
    t = time.time()
    pool, cl = build(cls, a.pattern, a.K)
    print('vars', pool.top, 'clauses', len(cl), 'build', round(time.time() - t, 1), flush=True)
    with Solver(name=a.solver, bootstrap_with=cl) as s:
        r = s.solve()
        print('RESULT', 'SAT' if r else 'UNSAT', 'side', a.side, 'pattern', a.pattern, 'K', a.K,
              'secs', round(time.time() - t, 1), flush=True)
        if r:
            ops, code = extract(s.get_model(), pool, a.pattern)
            fin = simulate(ops)
            codes = [tuple(fin[p][w] for w in code) for p in range(NP)]
            ok = all(cls[p] == cls[q] for p in range(NP) for q in range(NP) if codes[p] == codes[q])
            print('verified class code:', ok, 'code wires', code, 'distinct codes', len(set(codes)))
            for l, layer in zip(a.pattern, ops): print(' ', l, layer)
            if a.out:
                json.dump(dict(side=a.side, pattern=a.pattern, K=a.K, ops=ops, code=code), open(a.out, 'w'))
