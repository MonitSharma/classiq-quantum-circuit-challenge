"""Abstract-stage SAT: stage = up to 3 Toffolis given by linear forms (alpha, beta) on the
current 9 wires and fan-out target vectors lambda, with alpha.lambda = beta.lambda = 0,
rank(alpha,beta)=6, rank(lambda)=3 (physically: CX-conjugated batch of 3 disjoint Toffolis).
Separation via class/code-value occupancy."""
import sys, time, json
from pysat.solvers import Solver
from pysat.card import CardEnc, EncType
from satenc import CNF
from classes import ROWCLS, COLCLS

def dot_const(c, vec_vars, bits):
    return c.XORs([vec_vars[j] for j in range(len(bits)) if bits[j]])

def build(cls, T, ncode=4, W=9, rank=True):
    c = CNF(); X = range(64)
    w = [[c.const((x >> k) & 1) if k < 6 else -c.T for x in X] for k in range(W)]
    rec = []
    for t in range(T):
        A = [[c.new() for j in range(W)] for i in range(6)]   # rows: a1,b1,a2,b2,a3,b3
        Lm = [[c.new() for j in range(W)] for i in range(3)]  # lambda_i
        rec.append((A, Lm))
        for i in range(6):
            for l in range(3):
                s = c.XORs([c.AND(A[i][j], Lm[l][j]) for j in range(W)])
                c.clauses.append([-s])
        if rank:
            R = [[c.new() for k in range(6)] for j in range(W)]
            for i in range(6):
                for k in range(6):
                    s = c.XORs([c.AND(A[i][j], R[j][k]) for j in range(W)])
                    c.clauses.append([s] if i == k else [-s])
            S = [[c.new() for j in range(W)] for k in range(3)]
            for k in range(3):
                for l in range(3):
                    s = c.XORs([c.AND(S[k][j], Lm[l][j]) for j in range(W)])
                    c.clauses.append([s] if k == l else [-s])
        ab = [[c.XORs([c.AND(A[i][j], w[j][x]) for j in range(W)]) for x in X] for i in range(6)]
        prods = [[c.AND(ab[2 * i][x], ab[2 * i + 1][x]) for x in X] for i in range(3)]
        nw = []
        for k in range(W):
            nw.append([c.XORs([w[k][x]] + [c.AND(Lm[i][k], prods[i][x]) for i in range(3)]) for x in X])
        w = nw
    G = [[c.new() for j in range(W)] for r in range(ncode)]
    code = [[c.XORs([c.AND(G[r][j], w[j][x]) for j in range(W)]) for x in X] for r in range(ncode)]
    ncls = max(cls) + 1
    occ = [[c.new() for v in range(1 << ncode)] for k in range(ncls)]
    for x in X:
        for v in range(1 << ncode):
            cl = [(-code[r][x] if (v >> r) & 1 else code[r][x]) for r in range(ncode)]
            c.clauses.append(cl + [occ[cls[x]][v]])
    for v in range(1 << ncode):
        for k1 in range(ncls):
            for k2 in range(k1 + 1, ncls):
                c.clauses.append([-occ[k1][v], -occ[k2][v]])
    return c, rec, G

if __name__ == '__main__':
    side, T = sys.argv[1], int(sys.argv[2])
    solver = sys.argv[3] if len(sys.argv) > 3 else 'cadical195'
    cls = COLCLS if side == 'x' else ROWCLS
    t0 = time.time()
    c, rec, G = build(cls, T)
    print(f"side={side} T={T} vars={c.pool.top} clauses={len(c.clauses)} {solver}", flush=True)
    with Solver(name=solver, bootstrap_with=c.clauses) as s:
        ok = s.solve()
        print("SAT" if ok else "UNSAT", f"{time.time()-t0:.1f}s", flush=True)
        if ok:
            ms = set(l for l in s.get_model() if l > 0)
            v = lambda z: 1 if z in ms else 0
            out = dict(side=side, T=T, stages=[dict(A=[[v(z) for z in row] for row in A], L=[[v(z) for z in row] for row in Lm]) for A, Lm in rec],
                       G=[[v(z) for z in row] for row in G])
            json.dump(out, open(f"enc3_{side}_T{T}_{solver}.json", "w"))
