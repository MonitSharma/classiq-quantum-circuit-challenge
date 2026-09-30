"""2 in-place code wires + 2 ancilla bits: 4 blocks of 16, <=4 classes each.
Rows = cosets of the 2-dim target subspace (16 rows of 4)."""
import sys, itertools, json, time; sys.path.insert(0,'src')
from collections import Counter
from z3 import Bool, Solver, Implies, PbLe, PbEq, sat, unsat
import two_stage_oracle as ts

def subspaces2():
    seen=set(); out=[]
    for a,b in itertools.combinations(range(1,64),2):
        S={0,a,b,a^b}
        if len(S)!=4: continue
        k=frozenset(S)
        if k in seen: continue
        seen.add(k); out.append((sorted(S),(a,b)))
    return out
def solve(rows, cls, nb=4, cap=4, timeout=15000):
    classes=sorted(set(cls)); R=len(rows); n=len(rows[0])
    A=[[[Bool(f'a{f}_{t}_{b}') for b in range(nb)] for t in range(n)] for f in range(R)]
    U=[[Bool(f'u{b}_{c}') for c in range(len(classes))] for b in range(nb)]
    S=Solver(); S.set('timeout',timeout)
    for f in range(R):
        for t in range(n): S.add(PbEq([(A[f][t][b],1) for b in range(nb)],1))
        for b in range(nb): S.add(PbEq([(A[f][t][b],1) for t in range(n)],1))
        for t in range(n):
            ci=classes.index(cls[rows[f][t]])
            for b in range(nb): S.add(Implies(A[f][t][b],U[b][ci]))
    for b in range(nb): S.add(PbLe([(U[b][i],1) for i in range(len(classes))],cap))
    r=S.check()
    if r==sat:
        m=S.model()
        return [[next(b for b in range(nb) if m[A[f][t][b]]) for t in range(n)] for f in range(R)], \
               [[classes[i] for i in range(len(classes)) if m[U[b][i]]] for b in range(nb)]
    return None if r==unsat else 'timeout'
W2=subspaces2()
print('2-dim subspaces:',len(W2))
out={}
for name,cls in (('y',ts.ROWCLS),('x',ts.COLCLS)):
    tot=Counter(cls); cands=[]
    for W,gen in W2:
        seen=set(); rows=[]
        for y in range(64):
            if y in seen: continue
            co=[y^w for w in W]; seen.update(co); rows.append(co)
        need=sum(max(max(sum(1 for t in r if cls[t]==c) for r in rows), -(-n//16)) for c,n in tot.items())
        cands.append((need,W,gen,rows))
    cands.sort(key=lambda z:z[0])
    ok=[c for c in cands if c[0]<=16]
    print(f'{name}: slot bounds best {[c[0] for c in cands[:6]]}; {len(ok)} within budget',flush=True)
    got=None; t0=time.time(); to=0
    for need,W,gen,rows in ok:
        if time.time()-t0>120: break
        r=solve(rows,cls)
        if r=='timeout': to+=1; continue
        if r: got=(W,gen,rows,r); break
    if got:
        print(f'  SAT  W={got[0]} generators={got[1]}')
        print(f'  block class-sets={got[3][1]}',flush=True)
        out[name]={'W':list(got[0]),'gen':list(got[1]),
                   'rows':[list(r) for r in got[2]],
                   'assign':got[3][0],'blocks':got[3][1]}
    else:
        print(f'  none found ({to} timeouts, {int(time.time()-t0)}s)',flush=True)
json.dump(out,open(sys.argv[1],'w'))
