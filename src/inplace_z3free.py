"""Unrestricted: any bijection per row. Is '8 blocks, <=2 classes' achievable at all?"""
import sys, itertools, json, time; sys.path.insert(0,'src')
from collections import Counter
from z3 import Bool, Solver, Implies, PbLe, PbEq, sat, unsat
import two_stage_oracle as ts
exec(open(sys.argv[2]).read().split("def coords")[0].split("import two_stage_oracle as ts")[1]) if False else None
def subspaces3():
    seen=set(); out=[]
    for b in itertools.combinations(range(1,64),3):
        S={0}
        for m in range(1,8):
            v=0
            for i in range(3):
                if m>>i&1: v^=b[i]
            S.add(v)
        if len(S)!=8: continue
        k=frozenset(S)
        if k in seen: continue
        seen.add(k); out.append((sorted(S),b))
    return out
def solve_rows(rows, cls, cap=2, timeout=30000):
    classes=sorted(set(cls))
    R=len(rows)
    A=[[[Bool(f'a{f}_{t}_{b}') for b in range(8)] for t in range(8)] for f in range(R)]
    U=[[Bool(f'u{b}_{c}') for c in range(len(classes))] for b in range(8)]
    S=Solver(); S.set('timeout',timeout)
    for f in range(R):
        for t in range(8): S.add(PbEq([(A[f][t][b],1) for b in range(8)],1))
        for b in range(8): S.add(PbEq([(A[f][t][b],1) for t in range(8)],1))
        for t in range(8):
            ci=classes.index(cls[rows[f][t]])
            for b in range(8): S.add(Implies(A[f][t][b],U[b][ci]))
    for b in range(8): S.add(PbLe([(U[b][i],1) for i in range(len(classes))],cap))
    r=S.check()
    if r==sat:
        m=S.model()
        return [[next(b for b in range(8) if m[A[f][t][b]]) for t in range(8)] for f in range(R)], \
               [[classes[i] for i in range(len(classes)) if m[U[b][i]]] for b in range(8)]
    return None if r==unsat else 'timeout'
W3=subspaces3()
out={}
for name,cls in (('y',ts.ROWCLS),('x',ts.COLCLS)):
    tot=Counter(cls); cands=[]
    for W,bas in W3:
        seen=set(); rows=[]
        for y in range(64):
            if y in seen: continue
            co=[y^w for w in W]; seen.update(co); rows.append(co)
        need=sum(max(max(sum(1 for t in r if cls[t]==c) for r in rows), -(-n//8)) for c,n in tot.items())
        if need<=16: cands.append((need,W,rows))
    cands.sort(key=lambda z:z[0])
    print(f'{name}: {len(cands)} candidates',flush=True)
    got=None; t0=time.time(); to=0
    for need,W,rows in cands:
        if time.time()-t0>1500: break
        r=solve_rows(rows,cls)
        if r=='timeout': to+=1; continue
        if r: got=(W,rows,r); break
    if got:
        print(f'  SAT with unrestricted permutations, W={got[0]}')
        print(f'  blocks={got[2][1]}',flush=True)
        out[name]={'W':list(got[0]),'rows':[list(r) for r in got[1]],
                   'assign':got[2][0],'blocks':got[2][1]}
    else:
        print(f'  UNSAT on all tried candidates ({to} timeouts, {int(time.time()-t0)}s)',flush=True)
json.dump(out,open(sys.argv[1],'w'))
