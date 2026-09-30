"""Physical SAT model: each stage = L CX layers (matchings) + free wire relabeling,
then up to 3 parallel Toffolis on roles (0,1->6),(2,3->7),(4,5->8) with enable bits.
Final: arbitrary 4-bit linear code of the 9 wires must separate classes."""
import sys, time, json
from pysat.solvers import Solver
from pysat.card import CardEnc, EncType
from satenc import CNF
from classes import ROWCLS, COLCLS

def amo(c, lits):
    enc = CardEnc.atmost(lits=lits, bound=1, top_id=c.pool.top, encoding=EncType.seqcounter)
    # sync pool
    c.pool.occupy(c.pool.top + 1, enc.nv)
    c.pool.top = max(c.pool.top, enc.nv)
    c.clauses += enc.clauses

def exactly_one(c, lits):
    c.clauses.append(list(lits)); amo(c, lits)

def build(cls, T, L, ncode=4, W=9, final_L=0):
    c = CNF(); X = range(64)
    w = [[c.const((x >> k) & 1) if k < 6 else -c.T for x in X] for k in range(W)]
    rec = dict(cx=[], perm=[], en=[])
    def cx_layers(w, nl):
        layers = []
        for l in range(nl):
            e = {(i, j): c.new() for i in range(W) for j in range(W) if i != j}
            for q in range(W):
                amo(c, [e[(i, j)] for (i, j) in e if i == q or j == q])
            nw = []
            for j in range(W):
                nw.append([c.XORs([w[j][x]] + [c.AND(e[(i, j)], w[i][x]) for i in range(W) if i != j]) for x in X])
            w = nw; layers.append(e)
        return w, layers
    for t in range(T):
        w, layers = cx_layers(w, L)
        rec['cx'].append(layers)
        P = [[c.new() for j in range(W)] for k in range(W)]
        for k in range(W): exactly_one(c, P[k])
        for j in range(W): exactly_one(c, [P[k][j] for k in range(W)])
        u = []
        for k in range(W):
            row = []
            for x in X:
                o = c.new()
                terms = [c.AND(P[k][j], w[j][x]) for j in range(W)]
                # o == OR(terms) (exactly one P selected)
                c.clauses.append([-o] + terms)
                for tm in terms: c.clauses.append([o, -tm])
                row.append(o)
            u.append(row)
        rec['perm'].append(P)
        nw = [row[:] for row in u]
        ens = []
        for i in range(3):
            en = c.new(); ens.append(en)
            for x in X:
                p = c.AND(en, c.AND(u[2 * i][x], u[2 * i + 1][x]))
                nw[6 + i][x] = c.XOR(u[6 + i][x], p)
        rec['en'].append(ens)
        w = nw
    G = [[c.new() for j in range(W)] for r in range(ncode)]
    code = [[c.XORs([c.AND(G[r][j], w[j][x]) for j in range(W)]) for x in X] for r in range(ncode)]
    for a in X:
        for b in range(a + 1, 64):
            if cls[a] != cls[b]:
                c.clauses.append([c.XOR(code[r][a], code[r][b]) for r in range(ncode)])
    rec['G'] = G
    return c, rec

def val(model_set, v):
    return 1 if v in model_set else 0

if __name__ == '__main__':
    side, T, L = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    solver = sys.argv[4] if len(sys.argv) > 4 else 'cadical195'
    cls = COLCLS if side == 'x' else ROWCLS
    t0 = time.time()
    c, rec = build(cls, T, L)
    print(f"side={side} T={T} L={L} vars={c.pool.top} clauses={len(c.clauses)} {solver}", flush=True)
    with Solver(name=solver, bootstrap_with=c.clauses) as s:
        ok = s.solve()
        print("SAT" if ok else "UNSAT", f"{time.time()-t0:.1f}s", flush=True)
        if ok:
            ms = set(l for l in s.get_model() if l > 0)
            out = dict(side=side, T=T, L=L,
                       cx=[[[ [i, j] for (i, j), v in layer.items() if val(ms, v)] for layer in layers] for layers in rec['cx']],
                       perm=[[[val(ms, v) for v in row] for row in P] for P in rec['perm']],
                       en=[[val(ms, v) for v in e] for e in rec['en']],
                       G=[[val(ms, v) for v in row] for row in rec['G']])
            json.dump(out, open(f"enc2_{side}_T{T}_L{L}.json", "w"))
