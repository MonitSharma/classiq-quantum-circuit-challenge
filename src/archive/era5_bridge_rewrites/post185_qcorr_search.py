"""Exact search: label bit b_j(x) = U_j(coset_W(x)) XOR q_j(x), q_j a product of two
affine forms (or zero). Label must be class-injective within each parity p.
Reduces to linear algebra: q_j - (node function) must be a coset function."""
import itertools, sys, json
import numpy as np
from post185_qcorr_oracle import logo, par

def classes():
    R={};ROW=[0]*64;C={};COL=[0]*64
    for y in range(64): ROW[y]=R.setdefault(tuple(int(logo(x,y)) for x in range(64)),len(R))
    for x in range(64): COL[x]=C.setdefault(tuple(int(logo(x,y)) for y in range(64)),len(C))
    return ROW,COL

def tt(fn): return sum(1<<x for x in range(64) if fn(x))

QS={}
for a in range(64):
    for ca in (0,1):
        for b in range(a,64):
            for cb in (0,1):
                t=tt(lambda x:(par(x,a)^ca)&(par(x,b)^cb))
                if t and t!=(1<<64)-1 and t not in QS and a and b and a!=b:
                    QS[t]=((a,ca),(b,cb))
QLIST=list(QS.items())

def subspaces(dim):
    seen=set();out=[]
    for bb in itertools.combinations(range(1,64),dim):
        S={0}
        for e in bb: S|={s^e for s in S}
        if len(S)!=1<<dim: continue
        t=frozenset(S)
        if t not in seen: seen.add(t); out.append((bb,sorted(S)))
    return out

class Basis:
    def __init__(s): s.piv={}
    def red(s,v,track=0):
        while v:
            i=v.bit_length()-1
            if i not in s.piv: return v,track
            pv,pt=s.piv[i]; v^=pv; track^=pt
        return 0,track
    def add(s,v,tag):
        r,t=s.red(v,tag)
        if r: s.piv[r.bit_length()-1]=(r,t); return True
        return False

def run(cls,dim,maxq=3,report=5):
    results=[]
    for bb,W in subspaces(dim):
        coset=[0]*64; reps={}
        for x in range(64):
            coset[x]=reps.setdefault(min(x^w for w in W),len(reps))
        nc=len(reps)
        for p in range(1,64):
            nodes={}
            node=[nodes.setdefault((par(x,p),cls[x]),len(nodes)) for x in range(64)]
            nn=len(nodes)
            # basis: node indicators tagged with bit n (low bits), coset indicators tagged high
            B=Basis()
            for n in range(nn):
                B.add(tt(lambda x:node[x]==n), 1<<n)
            for c in range(nc):
                B.add(tt(lambda x:coset[x]==c), 1<<(nn+c))
            # K: node-vectors that are also coset functions -> from dependencies
            K=Basis(); kvecs=[]
            # node-function g(nodevec) equals coset function iff constant on each coset
            # compute by testing basis of node space: solve via reduce of combos is costly; use components
            parent=list(range(nn))
            def f(a):
                while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
                return a
            for c in range(nc):
                ns=[node[x] for x in range(64) if coset[x]==c]
                for u in ns[1:]: parent[f(u)]=f(ns[0])
            comps={}
            for n in range(nn): comps.setdefault(f(n),[]).append(n)
            kgen=[sum(1<<n for n in cm) for cm in comps.values()]
            Kspan={0}
            if len(kgen)>12: continue
            for g in kgen: Kspan|={k^g for k in Kspan}
            # node-parts of admissible q
            parts={0:None}
            for t,meta in QLIST:
                r,track=B.red(t)
                if r: continue
                nv=track&((1<<nn)-1)
                key=min(nv^k for k in Kspan)
                if key not in parts: parts[key]=meta
            # candidate bit vectors: part ^ k
            groups={0:[n for (pp,c),n in nodes.items() if pp==0],1:[n for (pp,c),n in nodes.items() if pp==1]}
            cand={}
            for key,meta in parts.items():
                for k in Kspan:
                    v=key^k
                    cost=0 if meta is None else 1
                    if v not in cand or cand[v][0]>cost: cand[v]=(cost,meta)
            vl=list(cand.items())
            best=None
            for (v0,m0),(v1,m1) in itertools.combinations(vl,2):
                c01=m0[0]+m1[0]
                if best is not None and c01>=best[0]: continue
                bad=False
                for g in groups.values():
                    cnt={}
                    for n in g:
                        kk=((v0>>n)&1,(v1>>n)&1); cnt[kk]=cnt.get(kk,0)+1
                        if cnt[kk]>2: bad=True;break
                    if bad:break
                if bad: continue
                for v2,m2 in vl:
                    cst=c01+m2[0]
                    if best is not None and cst>=best[0]: continue
                    ok=True
                    for g in groups.values():
                        seen=set()
                        for n in g:
                            code=((v0>>n)&1)|((v1>>n)&1)<<1|((v2>>n)&1)<<2
                            if code in seen: ok=False;break
                            seen.add(code)
                        if not ok: break
                    if ok: best=(cst,(v0,m0[1]),(v1,m1[1]),(v2,m2[1]))
            if best is not None and best[0]<=maxq:
                results.append((best[0],bb,p,best,nodes))
                if best[0]==0 or len(results)>=report and min(r[0] for r in results)<=1:
                    pass
    results.sort(key=lambda r:r[0])
    return results

if __name__=='__main__':
    name=sys.argv[1]; dim=int(sys.argv[2])
    ROW,COL=classes()
    res=run(COL if name=='x' else ROW,dim)
    print(name,"dim",dim,"solutions:",len(res),"min RCCX corrections:",res[0][0] if res else None,flush=True)
    import pickle
    pickle.dump([(r[0],r[1],r[2],r[3],r[4]) for r in res[:200]],open(f'/tmp/scratch/qsol_{name}_{dim}.pkl','wb'))
