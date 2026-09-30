"""SAT model: 9-wire reversible encoder = T batches of (free GL(9) map, 3 parallel Toffolis
on fixed wire roles (0,1->6),(2,3->7),(4,5->8)); final 4-bit linear code must separate classes."""
import sys, time, itertools, json
from pysat.formula import IDPool
from pysat.solvers import Solver
from classes import ROWCLS, COLCLS

class CNF:
    def __init__(self):
        self.pool = IDPool(); self.clauses = []
        self.T = self.new(); self.clauses.append([self.T])
    def new(self):
        return self.pool.id(('aux', len(self.pool.obj2id)))
    def const(self, b):
        return self.T if b else -self.T
    def AND(self, a, b):
        if a == -self.T or b == -self.T: return -self.T
        if a == self.T: return b
        if b == self.T: return a
        o = self.new(); self.clauses += [[-o, a], [-o, b], [o, -a, -b]]; return o
    def XOR(self, a, b):
        if a == -self.T: return b
        if b == -self.T: return a
        if a == self.T: return -b
        if b == self.T: return -a
        o = self.new()
        self.clauses += [[-o, a, b], [-o, -a, -b], [o, -a, b], [o, a, -b]]
        return o
    def XORs(self, lits):
        acc = -self.T
        for l in lits: acc = self.XOR(acc, l)
        return acc

def build(cls, T, ncode=4, W=9, invert=True):
    c = CNF()
    X = range(64)
    w = [[c.const((x >> k) & 1) if k < 6 else -c.T for x in X] for k in range(W)]
    Ms = []
    for t in range(T):
        M = [[c.new() for j in range(W)] for k in range(W)]
        Ms.append(M)
        if invert:
            N = [[c.new() for j in range(W)] for k in range(W)]
            for i in range(W):
                for k in range(W):
                    s = c.XORs([c.AND(M[i][j], N[j][k]) for j in range(W)])
                    c.clauses.append([s] if i == k else [-s])
        u = [[c.XORs([c.AND(M[k][j], w[j][x]) for j in range(W)]) for x in X] for k in range(W)]
        nw = [row[:] for row in u]
        for i in range(3):
            for x in X:
                p = c.AND(u[2 * i][x], u[2 * i + 1][x])
                nw[6 + i][x] = c.XOR(u[6 + i][x], p)
        w = nw
    G = [[c.new() for j in range(W)] for r in range(ncode)]
    code = [[c.XORs([c.AND(G[r][j], w[j][x]) for j in range(W)]) for x in X] for r in range(ncode)]
    npairs = 0
    for a in X:
        for b in range(a + 1, 64):
            if cls[a] != cls[b]:
                c.clauses.append([c.XOR(code[r][a], code[r][b]) for r in range(ncode)]); npairs += 1
    return c, Ms, G, npairs

def decode(model, c, Ms, G):
    s = set(l for l in model if l > 0)
    val = lambda v: 1 if v in s else 0
    return [[[val(v) for v in row] for row in M] for M in Ms], [[val(v) for v in row] for row in G]

if __name__ == '__main__':
    side, T = sys.argv[1], int(sys.argv[2])
    ncode = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    cls = COLCLS if side == 'x' else ROWCLS
    t0 = time.time()
    c, Ms, G, npairs = build(cls, T, ncode)
    print(f"side={side} T={T} vars={c.pool.top} clauses={len(c.clauses)} pairs={npairs} build={time.time()-t0:.1f}s", flush=True)
    with Solver(name='cadical195', bootstrap_with=c.clauses) as s:
        ok = s.solve()
        print("SAT" if ok else "UNSAT", f"{time.time()-t0:.1f}s", flush=True)
        if ok:
            Mv, Gv = decode(s.get_model(), c, Ms, G)
            json.dump(dict(side=side, T=T, M=Mv, G=Gv), open(f"enc_{side}_T{T}_c{ncode}.json", "w"))
