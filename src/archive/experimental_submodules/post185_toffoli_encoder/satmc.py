"""Minimum AND count (no wire limit) of a separating 4-bit linear code over an XAG."""
import sys, time, json
from pysat.solvers import Solver
from satenc import CNF
from classes import ROWCLS, COLCLS

def build(cls, k, ncode=4, maxdepth=None):
    c = CNF(); X = range(64)
    sig = [[c.const((x >> i) & 1) for x in X] for i in range(6)]
    level = [0] * 6
    gates = []
    for j in range(k):
        n = len(sig)
        a = [c.new() for _ in range(n)]; b = [c.new() for _ in range(n)]
        gates.append((a, b))
        # symmetry breaking: lexicographic-ish a < b skipped
        av = [c.XORs([c.AND(a[i], sig[i][x]) for i in range(n)]) for x in X]
        bv = [c.XORs([c.AND(b[i], sig[i][x]) for i in range(n)]) for x in X]
        sig.append([c.AND(av[x], bv[x]) for x in X])
        if maxdepth is not None and j >= 3 * 1:  # optional depth handled by caller layout
            pass
    n = len(sig)
    G = [[c.new() for _ in range(n)] for r in range(ncode)]
    code = [[c.XORs([c.AND(G[r][i], sig[i][x]) for i in range(n)]) for x in X] for r in range(ncode)]
    ncls = max(cls) + 1
    occ = [[c.new() for v in range(1 << ncode)] for kk in range(ncls)]
    for x in X:
        for v in range(1 << ncode):
            cl = [(-code[r][x] if (v >> r) & 1 else code[r][x]) for r in range(ncode)]
            c.clauses.append(cl + [occ[cls[x]][v]])
    for v in range(1 << ncode):
        for k1 in range(ncls):
            for k2 in range(k1 + 1, ncls):
                c.clauses.append([-occ[k1][v], -occ[k2][v]])
    return c, gates, G

if __name__ == '__main__':
    side, k = sys.argv[1], int(sys.argv[2])
    cls = COLCLS if side == 'x' else ROWCLS
    t0 = time.time(); c, gates, G = build(cls, k)
    print(f"side={side} k={k} vars={c.pool.top} clauses={len(c.clauses)}", flush=True)
    with Solver(name='cadical195', bootstrap_with=c.clauses) as s:
        ok = s.solve(); print("SAT" if ok else "UNSAT", f"{time.time()-t0:.1f}s", flush=True)
        if ok:
            ms = set(l for l in s.get_model() if l > 0); v = lambda z: 1 if z in ms else 0
            json.dump(dict(side=side, k=k, gates=[[[v(z) for z in a], [v(z) for z in b]] for a, b in gates], G=[[v(z) for z in r] for r in G]), open(f"mc_{side}_k{k}.json", "w"))
