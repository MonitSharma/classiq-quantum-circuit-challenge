"""Mod-2pi lift for the CONDITIONAL loader targets: random integer shifts z of the RHS."""
import numpy as np, sys, pickle, time
from scipy.optimize import linprog
from codes import xcode, ycode, bits
from condlp import atoms_for
def sparse_rep_w(target,A,w0,iters=8,eps=1e-3,tol=1e-7):
    K=A.shape[1]; w=w0.copy(); best=None
    for it in range(iters):
        r=linprog(np.concatenate([w,w]),A_eq=np.hstack([A,-A]),b_eq=target,bounds=(0,None),method='highs')
        if r.status!=0: break
        a=r.x[:K]-r.x[K:]
        sup=np.where(np.abs(a)>tol)[0]
        sol,*_=np.linalg.lstsq(A[:,sup],target,rcond=None)
        if np.max(np.abs(A[:,sup]@sol-target))<1e-9:
            if best is None or len(sup)<best[0]: best=(len(sup),sup,sol)
        w=w0/(np.abs(a)+eps)
    return best
if __name__=='__main__':
    src=sys.argv[1]; tgt=int(sys.argv[2]); ntry=int(sys.argv[3]); seed=int(sys.argv[4])
    D=pickle.load(open(src,'rb'))
    side=D['side']; cols=D['cols']; cond=D['cond']
    code = xcode if side=='x' else ycode
    B=bits(code)
    Bn=np.array([sum(B[i] for i in range(3) if cols[j]>>i&1)%2 for j in range(3)])
    keys,A=atoms_for(Bn,cond[tgt])
    L=Bn[tgt].astype(float)
    rng=np.random.default_rng(seed)
    K=A.shape[1]
    base=np.ones(K)
    r=sparse_rep_w(np.pi*L,A,base)
    best=(r[0],np.zeros(64,int),r[1],r[2]); print('z=0 support',r[0],flush=True)
    pool={}
    def record(cnt,sup,sol):
        key=tuple(sorted(sup))
        if key in pool: return
        pool[key]=(cnt,sup,sol)
    record(r[0],r[1],r[2])
    t0=time.time()
    cur=np.zeros(64,int); curc=best[0]
    for it in range(ntry):
        if it%3==0:
            nz=rng.integers(1,6); z=np.zeros(64,int)
            idx=rng.choice(64,size=nz,replace=False); z[idx]=rng.choice([-1,1],size=nz)
        else:
            z=cur.copy(); nz=rng.integers(1,4)
            idx=rng.choice(64,size=nz,replace=False)
            for j in idx: z[j]+=int(rng.choice([-1,1]))
        w=np.ones(K)+0.25*rng.random(K)
        rr=sparse_rep_w(np.pi*(L+2*z),A,w)
        if rr is None: continue
        if rr[0]<=curc: cur=z.copy(); curc=rr[0]
        if rr[0]<=best[0]+2: record(rr[0],rr[1],rr[2])
        if rr[0]<best[0]:
            best=(rr[0],z.copy(),rr[1],rr[2]); print(' it',it,'support',rr[0],flush=True)
    print('best support',best[0],'time',round(time.time()-t0,1),flush=True)
    np.save(f'runs/liftc_{side}_{tgt}_z.npy',best[1])
    def emit(sup,sol):
        par={}
        for k,coef in zip(sup,sol):
            s_,sub=keys[k]; mask=(1<<(6+tgt))|s_
            for j in sub: mask|=1<<(6+j)
            par[mask]=par.get(mask,0.0)+coef
        return par
    pickle.dump(emit(best[2],best[3]),open(f'runs/liftc_{side}_{tgt}_par.pkl','wb'))
    items=sorted(pool.values(),key=lambda t:t[0])[:8]
    for i,(cnt,sup,sol) in enumerate(items):
        pickle.dump(emit(sup,sol),open(f'runs/liftc_{side}_{tgt}_p{i}.pkl','wb'))
    print('pool emitted',[t[0] for t in items],flush=True)
