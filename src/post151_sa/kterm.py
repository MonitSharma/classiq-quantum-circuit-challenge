"""Kernel term estimate for an arbitrary code design (nbx + nby code bits)."""
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
from logo import logo_pixel
M=np.array([[1.0 if logo_pixel(x,y) else 0.0 for y in range(64)] for x in range(64)])
def chi_mat(n):
    N=1<<n
    A=np.empty((N,N))
    for m in range(N):
        for c in range(N): A[m,c]=-1.0 if bin(m&c).count('1')&1 else 1.0
    return A
_CH={}
def chi(n):
    if n not in _CH: _CH[n]=chi_mat(n)
    return _CH[n]
def table(xcode,ycode,nbx,nby):
    NX=1<<nbx; NY=1<<nby
    T=np.full((NX,NY),-1.0)
    for x in range(64):
        cx=xcode[x]
        for y in range(64):
            v=M[x,y]; cy=ycode[y]
            if T[cx,cy]>=0 and T[cx,cy]!=v: return None
            T[cx,cy]=v
    return T
def terms(T,nbx,nby,rounds=8,verbose=False):
    NX=1<<nbx; NY=1<<nby; N=NX*NY
    F=T.reshape(-1)
    known=F>=0
    R=np.where(known)[0]; U=np.where(~known)[0]
    CH=np.kron(chi(nbx),chi(nby))/N          # (N x N) rows=mask, cols=code
    r0=CH[:,R]@F[R]
    XU=CH[:,U]
    u=np.zeros(len(U)); w=np.ones(N); w[0]=0; best=None; bestv=None
    nu=len(U)
    for it in range(rounds):
        base=r0+XU@u; n=np.round(base)
        c=np.concatenate([np.zeros(nu),w])
        A=np.vstack([np.hstack([XU,-np.eye(N)]),np.hstack([-XU,-np.eye(N)])])
        b=np.concatenate([-(base-n),(base-n)])
        res=linprog(c,A_ub=csr_matrix(A),b_ub=b,bounds=[(None,None)]*nu+[(0,None)]*N,method='highs')
        if not res.success: break
        u=u+res.x[:nu]
        bb=r0+XU@u; d=bb[1:]-np.round(bb[1:]); k=int(np.sum(np.abs(d)>1e-7))
        if best is None or k<best: best=k; bestv=u.copy()
        w=1.0/(np.abs(np.concatenate([[0],d]))+1e-3); w[0]=0
        if verbose: print(' it',it,'terms',k,flush=True)
    return best,bestv
