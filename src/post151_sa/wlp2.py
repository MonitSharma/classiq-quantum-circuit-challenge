import numpy as np, itertools, sys, pickle
from scipy.optimize import linprog
from condlp import atoms_for
from codes import *
def sparse_rep_w(target, A, keys, base, iters=12, eps=1e-3, tol=1e-7):
    K=A.shape[1]; w=base.copy(); best=None
    for it in range(iters):
        r=linprog(np.concatenate([w,w]),A_eq=np.hstack([A,-A]),b_eq=target,bounds=(0,None),method='highs')
        if r.status!=0: break
        a=r.x[:K]-r.x[K:]
        sup=np.where(np.abs(a)>tol)[0]
        sol,*_=np.linalg.lstsq(A[:,sup],target,rcond=None)
        if np.max(np.abs(A[:,sup]@sol-target))<1e-9:
            cost=sum(base[k] for k in sup)
            if best is None or cost<best[0]: best=(cost,sup,sol)
        w=base/(np.abs(a)+eps)
    return best[1],best[2]
def build(side, cols, cond, lam, wcond=1.0):
    code = xcode if side=='x' else ycode
    B=bits(code)
    Bn=np.array([sum(B[i] for i in range(3) if cols[j]>>i&1)%2 for j in range(3)])
    newcode=[int(Bn[0][v]|(Bn[1][v]<<1)|(Bn[2][v]<<2)) for v in range(64)]
    targets={}
    for i in range(3):
        keys,A=atoms_for(Bn,cond[i])
        base=np.array([1.0+lam*bin(k[0]).count('1')+ (wcond-1.0)*len(k[1]) for k in keys])
        sup,sol=sparse_rep_w(np.pi*Bn[i].astype(float),A,keys,base)
        par={}
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
    allw=set(range(9))
    return dict(side=side,cols=cols,cond=cond,targets=targets,gates=[],fix=[],req=req,al=[allw]*4,newcode=newcode,depth=None,placed=False)
if __name__=='__main__':
    side=sys.argv[1]; lam=float(sys.argv[2]); tag=sys.argv[3]
    if side=='x': cols=(1,6,2); cond={0:[],1:[0],2:[0]}
    else: cols=(1,2,4); cond={0:[],1:[0],2:[0]}
    D=build(side,cols,cond,lam)
    sizes={i:len([m for m,a in D['targets'][i].items() if abs(a)>1e-12]) for i in range(3)}
    wsum=sum(bin(m&63).count('1') for i in range(3) for m,a in D['targets'][i].items() if abs(a)>1e-12)
    print(side,'lam',lam,sizes,'total',sum(sizes.values()),'sum|s|',wsum,flush=True)
    pickle.dump(D,open(f'runs/wl_{tag}.pkl','wb'))
    pl=[(m,i) for i in range(3) for m,a in D['targets'][i].items() if abs(a)>1e-12]
    open(f'runs/wl_{tag}.lb','w').write('\n'.join([str(len(pl))]+[f'{m} {i}' for m,i in pl])+'\n')
