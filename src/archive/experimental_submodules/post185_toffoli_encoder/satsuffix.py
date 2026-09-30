"""SAT large-neighbourhood step: given fixed wire truth tables (after a prefix), find `free` abstract
stages + an ncode-bit separating code."""
import sys, time, json
from pysat.solvers import Solver
from satenc import CNF
from classes import ROWCLS, COLCLS

def build(cls, w0, free, ncode, W=9):
    c = CNF(); X = range(64)
    w = [[c.const((w0[k] >> x) & 1) for x in X] for k in range(W)]
    rec = []
    for t in range(free):
        A = [[c.new() for j in range(W)] for i in range(6)]
        Lm = [[c.new() for j in range(W)] for i in range(3)]
        rec.append((A, Lm))
        for i in range(6):
            for l in range(3):
                c.clauses.append([-c.XORs([c.AND(A[i][j], Lm[l][j]) for j in range(W)])])
        R = [[c.new() for k in range(6)] for j in range(W)]
        for i in range(6):
            for k in range(6):
                s = c.XORs([c.AND(A[i][j], R[j][k]) for j in range(W)]); c.clauses.append([s] if i == k else [-s])
        S = [[c.new() for j in range(W)] for k in range(3)]
        for k in range(3):
            for l in range(3):
                s = c.XORs([c.AND(S[k][j], Lm[l][j]) for j in range(W)]); c.clauses.append([s] if k == l else [-s])
        ab = [[c.XORs([c.AND(A[i][j], w[j][x]) for j in range(W)]) for x in X] for i in range(6)]
        prods = [[c.AND(ab[2 * i][x], ab[2 * i + 1][x]) for x in X] for i in range(3)]
        w = [[c.XORs([w[k][x]] + [c.AND(Lm[i][k], prods[i][x]) for i in range(3)]) for x in X] for k in range(W)]
    G = [[c.new() for j in range(W)] for r in range(ncode)]
    code = [[c.XORs([c.AND(G[r][j], w[j][x]) for j in range(W)]) for x in X] for r in range(ncode)]
    ncls = max(cls) + 1
    occ = [[c.new() for v in range(1 << ncode)] for k in range(ncls)]
    for x in X:
        for v in range(1 << ncode):
            c.clauses.append([(-code[r][x] if (v >> r) & 1 else code[r][x]) for r in range(ncode)] + [occ[cls[x]][v]])
    for v in range(1 << ncode):
        for k1 in range(ncls):
            for k2 in range(k1 + 1, ncls):
                c.clauses.append([-occ[k1][v], -occ[k2][v]])
    return c, rec, G

if __name__ == '__main__':
    side = sys.argv[1]; w0 = [int(h, 16) for h in sys.argv[2].split(',')]; free = int(sys.argv[3]); ncode = int(sys.argv[4])
    cls = COLCLS if side == 'x' else ROWCLS
    t0 = time.time(); c, rec, G = build(cls, w0, free, ncode)
    with Solver(name='cadical195', bootstrap_with=c.clauses) as s:
        ok = s.solve()
        res = dict(side=side, free=free, ncode=ncode, sat=ok, seconds=round(time.time() - t0, 1))
        if ok:
            ms = set(l for l in s.get_model() if l > 0); v = lambda z: 1 if z in ms else 0
            res['stages'] = [[[sum(v(A[2*i][j]) << j for j in range(9)), sum(v(A[2*i+1][j]) << j for j in range(9)), sum(v(Lm[i][j]) << j for j in range(9))] for i in range(3)] for A, Lm in rec]
            res['G'] = [sum(v(z) << j for j, z in enumerate(row)) for row in G]
        print(json.dumps(res), flush=True)
