import numpy as np, itertools
from scipy.optimize import linprog
from codes import H
def atoms_for(Lbits, cond):
    """Lbits: 3x64 0/1 array. cond: list of target indices allowed as conditioning vars.
    returns list of (s, bsubset tuple) and matrix 64 x K"""
    Lam = 1-2*Lbits
    keys=[]; cols=[]
    for r in range(len(cond)+1):
        for sub in itertools.combinations(cond, r):
            m=np.ones(64)
            for j in sub: m=m*Lam[j]
            for s in range(64):
                keys.append((s,sub)); cols.append(H[s]*m)
    return keys, np.array(cols).T
def sparse_rep(target, A, iters=8, eps=1e-3, tol=1e-7):
    K=A.shape[1]; w=np.ones(K); best=None
    for it in range(iters):
        c=np.concatenate([w,w])
        r=linprog(c,A_eq=np.hstack([A,-A]),b_eq=target,bounds=(0,None),method='highs')
        if r.status!=0: break
        a=r.x[:K]-r.x[K:]
        sup=np.where(np.abs(a)>tol)[0]
        # exact refit on support
        sol,*_=np.linalg.lstsq(A[:,sup],target,rcond=None)
        if np.max(np.abs(A[:,sup]@sol-target))<1e-9:
            if best is None or len(sup)<len(best[0]): best=(sup,sol)
        w=1/(np.abs(a)+eps)
    return best
def conditional_supports(Lbits, order, cond_of=None):
    """order: loading order of targets; cond_of[i]: list of targets i may condition on (must precede)."""
    out={}
    for pos,i in enumerate(order):
        cond = list(order[:pos]) if cond_of is None else list(cond_of[i])
        keys,A=atoms_for(Lbits,cond)
        sup,sol=sparse_rep(np.pi*Lbits[i].astype(float),A)
        par={}
        for k,coef in zip(sup,sol):
            s,sub=keys[k]
            mask=(1<<(6+i))|s
            for j in sub: mask|=1<<(6+j)
            par[mask]=par.get(mask,0.0)+coef
        out[i]=(par,cond)
    return out
