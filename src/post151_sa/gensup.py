"""Generate several LP support variants for a loader frame (random reweighting), dump .pkl/.lb."""
import sys, pickle, numpy as np, itertools
from scipy.optimize import linprog
from codes import *
from condlp import atoms_for
from mkD3 import dump
def sparse_rep_r(target,A,rng,eps=1e-3,tol=1e-7,iters=9,jit=0.35,geo=None,gam=0.0):
    K=A.shape[1]
    base=np.ones(K)+jit*rng.random(K)
    if geo is not None and gam>0: base=base*(1.0+gam*geo)
    w=base.copy(); best=None
    for it in range(iters):
        r=linprog(np.concatenate([w,w]),A_eq=np.hstack([A,-A]),b_eq=target,bounds=(0,None),method='highs')
        if r.status!=0: break
        a=r.x[:K]-r.x[K:]
        sup=np.where(np.abs(a)>tol)[0]
        sol,*_=np.linalg.lstsq(A[:,sup],target,rcond=None)
        if np.max(np.abs(A[:,sup]@sol-target))<1e-9:
            c=len(sup)
            if best is None or c<best[0]: best=(c,sup,sol)
        w=base/(np.abs(a)+eps)
    return None if best is None else (best[1],best[2])
def build(side,cols,cond,rng,jit,gam=0.0):
    code = xcode if side=='x' else ycode
    B=bits(code)
    Bn=np.array([sum(B[i] for i in range(3) if cols[j]>>i&1)%2 for j in range(3)])
    newcode=[int(Bn[0][v]|(Bn[1][v]<<1)|(Bn[2][v]<<2)) for v in range(64)]
    targets={}
    for i in range(3):
        keys,A=atoms_for(Bn,cond[i])
        geo=np.array([bin(k[0]).count('1') for k in keys],dtype=float) if gam>0 else None
        r=sparse_rep_r(np.pi*Bn[i].astype(float),A,rng,jit=jit,geo=geo,gam=gam)
        if r is None: return None
        sup,sol=r; par={}
        for k,coef in zip(sup,sol):
            s,sub=keys[k]; mask=(1<<(6+i))|s
            for j in sub: mask|=1<<(6+j)
            par[mask]=par.get(mask,0.0)+coef
        targets[i]=par
    Minv={}
    for i in range(3):
        for combo in range(1,8):
            v=0
            for j in range(3):
                if combo>>j&1: v^=cols[j]
            if v==(1<<i): Minv[i]=combo
    req=[0x30 if side=='x' else 0x20]+[sum(1<<(6+j) for j in range(3) if Minv[i]>>j&1) for i in range(3)]
    return dict(side=side,cols=cols,cond=cond,targets=targets,gates=[],fix=[],req=req,al=[set(range(9))]*4,newcode=newcode,depth=None,placed=False)
if __name__=='__main__':
    side=sys.argv[1]; cols=tuple(int(c) for c in sys.argv[2].split(',')); n=int(sys.argv[3]); seed=int(sys.argv[4])
    gam=float(sys.argv[5]) if len(sys.argv)>5 else 0.0
    cond={0:[],1:[0],2:[0]}
    rng=np.random.default_rng(seed)
    seen={}
    for t in range(n):
        D=build(side,cols,cond,rng,jit=0.35,gam=gam)
        if D is None: continue
        key=tuple(sorted(m for i in range(3) for m in D['targets'][i]))
        sz=[len(D['targets'][i]) for i in range(3)]
        if key in seen: continue
        seen[key]=1
        tag=f"gs_{side}_{seed}_{t}"
        dump(D,tag)
        print(tag,sz,'total',sum(sz),flush=True)
