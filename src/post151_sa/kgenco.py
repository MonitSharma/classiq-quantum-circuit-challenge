"""Randomised sparsification of the 8-bit kernel phase polynomial -> alternative CO arrays."""
import numpy as np, math, sys, os
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
from kterm import table, chi
import codes as C
def build_F():
    xc=[ (bin(v&48).count('1')%2) | (C.xcode[v]<<1) for v in range(64)]
    yc=[ (bin(v&32).count('1')%2) | (C.ycode[v]<<1) for v in range(64)]
    T=table(xc,yc,4,4); F=T.reshape(-1).copy()
    return F, F>=0
CH=np.kron(chi(4),chi(4))     # CH[m,c]
def solve(rng, rounds=10, jit=0.4, warm=None):
    F,known=build_F()
    R=np.where(known)[0]; U=np.where(~known)[0]
    N=256
    r0=CH[:,R]@F[R]/N
    XU=CH[:,U]/N
    nu=len(U)
    u=np.zeros(nu) if warm is None else warm.copy()
    w=np.ones(N)+jit*rng.random(N); w[0]=0
    best=None
    for it in range(rounds):
        base=r0+XU@u; n=np.round(base)
        c=np.concatenate([np.zeros(nu),w])
        A=np.vstack([np.hstack([XU,-np.eye(N)]),np.hstack([-XU,-np.eye(N)])])
        bb=np.concatenate([-(base-n),(base-n)])
        res=linprog(c,A_ub=csr_matrix(A),b_ub=bb,bounds=[(None,None)]*nu+[(0,None)]*N,method='highs')
        if not res.success: break
        u=u+res.x[:nu]
        b=r0+XU@u; d=b-np.round(b); d[0]=0
        k=int(np.sum(np.abs(d)>1e-7))
        if best is None or k<best[0]: best=(k,u.copy())
        w=1.0/(np.abs(d)+1e-3); w[0]=0
    if best is None: return None
    k,u=best
    b=r0+XU@u
    frac=b-np.round(b); frac[0]=0.0
    frac[np.abs(frac)<1e-9]=0.0
    return k, frac
def check(frac):
    F,known=build_F()
    ph=(CH.T@frac)
    d=ph[known]-F[known]
    d=d-d[0]
    return float(np.max(np.abs(np.remainder(d+1,2)-1)))
if __name__=='__main__':
    n=int(sys.argv[1]); seed=int(sys.argv[2]); warmflag=len(sys.argv)>3 and sys.argv[3]=='warm'
    rng=np.random.default_rng(seed)
    warm=None
    if warmflag:
        import math as _m
        from kdrv import CO as _CO
        F0,known0=build_F()
        b0=_CO/_m.pi
        ph=(CH.T@b0)
        U0=np.where(~known0)[0]
        warm_full=ph
        r0=CH[:,np.where(known0)[0]]@F0[np.where(known0)[0]]/256
        XU=CH[:,U0]/256
        # u such that r0+XU@u = b0  ->  solve least squares (XU is 256 x |U|)
        warm,*_=np.linalg.lstsq(XU,b0-r0,rcond=None)
        bb=r0+XU@warm; dd=bb-np.round(bb); dd[0]=0
        print('warm start terms',int(np.sum(np.abs(dd)>1e-7)),flush=True)
    seen={}
    for t in range(n):
        r=solve(rng,warm=warm)
        if r is None: continue
        k,frac=r
        err=check(frac)
        if err>1e-9: print('BAD',k,err,flush=True); continue
        key=tuple(np.nonzero(np.abs(frac)>1e-9)[0])
        if key in seen: continue
        seen[key]=1
        tag=f'co_{seed}_{t}'
        np.save(f'runs/{tag}.npy', frac*math.pi)
        print(tag,'terms',k,'err %.1e'%err,flush=True)
