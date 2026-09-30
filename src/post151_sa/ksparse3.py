import numpy as np, sys
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
M=np.load('runs/Mcode.npy')
R=[c for c in range(256) if M[c]>=0]; U=[c for c in range(256) if M[c]<0]
chi=np.array([[(-1.0)**bin(m&c).count('1') for c in range(256)] for m in range(256)])
r0=(chi[:,R]@M[R].astype(float))/256.0
XU=chi[:,U]/256.0
XR=2.0*chi[:,R]/256.0
def terms(b,tol=1e-7):
    d=b[1:]-np.round(b[1:]); return int(np.sum(np.abs(d)>tol))
def lp_u(w,base):
    """min sum w|base + XU u - n| with n = round(...) handled by using free integer n -> we pass n"""
    n=np.round(base)
    nu=XU.shape[1]; N=nu+256
    c=np.zeros(N); c[nu:]=w
    A=np.hstack([XU,-np.eye(256)]); B=np.hstack([-XU,-np.eye(256)])
    Am=csr_matrix(np.vstack([A,B])); bm=np.concatenate([-(base-n),(base-n)])
    res=linprog(c,A_ub=Am,b_ub=bm,bounds=[(None,None)]*nu+[(0,None)]*256,method='highs')
    return res
def lp_uv(w,base,u,v):
    nu=XU.shape[1]; nv=XR.shape[1]
    cur=base+XU@u+XR@v; n=np.round(cur)
    N=nu+nv+256
    c=np.zeros(N); c[nu+nv:]=w
    A=np.hstack([XU,XR,-np.eye(256)]); B=np.hstack([-XU,-XR,-np.eye(256)])
    Am=csr_matrix(np.vstack([A,B])); bm=np.concatenate([-(base-n),(base-n)])
    res=linprog(c,A_ub=Am,b_ub=bm,bounds=[(None,None)]*(nu+nv)+[(0,None)]*256,method='highs')
    return res,n
def eval_v(v,rounds=12,eps=1e-3):
    """best term count with integer lifts v, optimising u by reweighted L1"""
    base=r0+XR@v
    u=np.zeros(XU.shape[1]); w=np.ones(256); w[0]=0; best=None
    for it in range(rounds):
        res=lp_u(w,base+XU@u)
        if not res.success: break
        u=u+res.x[:XU.shape[1]]
        b=base+XU@u; d=b-np.round(b); k=terms(b)
        if best is None or k<best[0]: best=(k,u.copy())
        w=1.0/(np.abs(d)+eps); w[0]=0
    return best
def run(seed=0,jitter=0.3,outer=8):
    rng=np.random.default_rng(seed)
    v=np.zeros(XR.shape[1]); u=np.zeros(XU.shape[1])
    w=np.ones(256)*(1+jitter*rng.random(256)); w[0]=0
    best=None
    b0=eval_v(v)
    if b0: best=(b0[0],b0[1],v.copy()); print(' v=0 ->',b0[0],flush=True)
    for it in range(outer):
        res,n=lp_uv(w,r0,u,v)
        if not res.success: break
        nu=XU.shape[1]; nv=XR.shape[1]
        u=res.x[:nu]; vc=res.x[nu:nu+nv]
        vr=np.round(vc)
        e=eval_v(vr)
        if e and (best is None or e[0]<best[0]): best=(e[0],e[1],vr.copy())
        b=r0+XU@u+XR@vc; d=b-np.round(b)
        w=1.0/(np.abs(d)+1e-3); w[0]=0
        print(' outer',it,'cont terms',terms(b),'rounded ->',e[0] if e else None,flush=True)
    return best
if __name__=='__main__':
    seed=int(sys.argv[1]); jit=float(sys.argv[2])
    b=run(seed=seed,jitter=jit)
    print('seed',seed,'best terms',b[0],flush=True)
    np.savez(f'runs/ks3_{seed}.npz',u=b[1],v=b[2])
