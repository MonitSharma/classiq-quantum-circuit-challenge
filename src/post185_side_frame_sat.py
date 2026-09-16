"""Existence SAT for one axis encoder: B batches of up to 3 disjoint RCCX on 9
wires, arbitrary invertible affine frames between batches, and a 4-wire class
code taken as affine combinations of the final wires. Labels/networks free.
Batch slots: new wires (0,1,2),(3,4,5),(6,7,8) = (ctrlA, ctrlB, target)."""
import argparse, itertools, json, time
from pysat.formula import IDPool
from pysat.solvers import Solver
from post185_side_encoder_sat import classes

W = 9; NP = 64

def build(cls, B, K=4, pairs_limit=None):
    pool = IDPool(); cl = []
    V = lambda *k: pool.id(k)
    def xor2(z, a, b): cl.extend([[-z, a, b], [-z, -a, -b], [z, -a, b], [z, a, -b]])
    def and2(z, a, b): cl.extend([[-z, a], [-z, b], [z, -a, -b]])
    TRUE = V('true'); cl.append([TRUE])
    def xor_chain(tag, lits):
        if not lits: return -TRUE
        acc = lits[0]
        for i, l in enumerate(lits[1:]):
            z = V(tag, i); xor2(z, acc, l); acc = z
        return acc
    val = {}
    for w in range(W):
        for p in range(NP):
            bit = (p >> w) & 1 if w < 6 else 0
            val[0, w, p] = TRUE if bit else -TRUE
    for b in range(B):
        coef = [[V('k', b, j, i) for i in range(W)] for j in range(W)]
        const = [V('const', b, j) for j in range(W)]
        # invertibility: no nonempty subset of rows XORs to zero
        for r in range(1, 1 << W):
            rows = [j for j in range(W) if r >> j & 1]
            cols = []
            for i in range(W):
                cols.append(xor_chain(('inv', b, r, i), [coef[j][i] for j in rows]))
            cl.append(cols)
        # symmetry: the 3 slots are unordered only if identical usage; keep a<->b swap free
        pre = {}
        for j in range(W):
            for p in range(NP):
                terms = []
                for i in range(W):
                    z = V('t', b, j, i, p); v = val[b, i, p]
                    and2(z, coef[j][i], v); terms.append(z)
                pre[j, p] = xor_chain(('pre', b, j, p), terms + [const[j]])
        for s in range(3):
            a, c, t = 3 * s, 3 * s + 1, 3 * s + 2
            on = V('on', b, s)
            for j in (a, c):
                for p in range(NP): val[b + 1, j, p] = pre[j, p]
            for p in range(NP):
                prod = V('prod', b, s, p)
                cl.extend([[-prod, on], [-prod, pre[a, p]], [-prod, pre[c, p]], [prod, -on, -pre[a, p], -pre[c, p]]])
                z = V('new', b, t, p); xor2(z, pre[t, p], prod); val[b + 1, t, p] = z
    # code: K affine combos of final wires separating all conflict pairs
    cc = [[V('cc', k, w) for w in range(W)] for k in range(K)]
    for p in range(NP):
        for q in range(p + 1, NP):
            if cls[p] == cls[q]: continue
            ors = []
            for k in range(K):
                terms = []
                for w in range(W):
                    d = V('d', w, p, q)
                    if ('dd', w, p, q) not in pool.obj2id:
                        pool.id(('dd', w, p, q)); xor2(d, val[B, w, p], val[B, w, q])
                    z = V('cd', k, w, p, q); and2(z, cc[k][w], d); terms.append(z)
                ors.append(xor_chain(('cx', k, p, q), terms))
            cl.append(ors)
    return pool, cl, val

def evaluate(model, pool, B, val):
    m = set(l for l in model if l > 0)
    truth = lambda lit: (abs(lit) in m) == (lit > 0)
    frames = []
    for b in range(B):
        frames.append(dict(coef=[[int(truth(pool.obj2id[('k', b, j, i)])) for i in range(W)] for j in range(W)],
                           const=[int(truth(pool.obj2id[('const', b, j)])) for j in range(W)],
                           on=[int(truth(pool.obj2id[('on', b, s)])) for s in range(3)]))
    code = [[int(truth(pool.obj2id[('cc', k, w)])) for w in range(W)] for k in range(4)]
    return frames, code

def replay(frames, code, cls):
    outs = []
    for p in range(NP):
        s = [(p >> w) & 1 if w < 6 else 0 for w in range(W)]
        for f in frames:
            pre = [(sum(f['coef'][j][i] & s[i] for i in range(W)) + f['const'][j]) % 2 for j in range(W)]
            new = list(pre)
            for k in range(3):
                if f['on'][k]: new[3 * k + 2] ^= pre[3 * k] & pre[3 * k + 1]
            s = new
        outs.append(tuple(sum(code[k][w] & s[w] for w in range(W)) % 2 for k in range(4)))
    return all(cls[p] == cls[q] for p in range(NP) for q in range(NP) if outs[p] == outs[q]), len(set(outs))

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--side', choices='xy', required=True)
    ap.add_argument('--B', type=int, required=True)
    ap.add_argument('--solver', default='cadical195')
    ap.add_argument('--out')
    a = ap.parse_args()
    ROW, COL = classes(); cls = COL if a.side == 'x' else ROW
    t = time.time(); pool, cl, val = build(cls, a.B)
    print('vars', pool.top, 'clauses', len(cl), 'build', round(time.time() - t, 1), flush=True)
    with Solver(name=a.solver, bootstrap_with=cl) as s:
        r = s.solve()
        print('RESULT', 'SAT' if r else 'UNSAT', a.side, 'B', a.B, 'solver', a.solver, 'secs', round(time.time() - t, 1), flush=True)
        if r:
            frames, code = evaluate(s.get_model(), pool, a.B, val)
            print('replay', replay(frames, code, cls), flush=True)
            if a.out: json.dump(dict(side=a.side, B=a.B, frames=frames, code=code), open(a.out, 'w'))
