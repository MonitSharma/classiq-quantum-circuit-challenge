"""kgenw.py n seed lamX lamY [out_prefix]: weighted sparsification of the kernel phase polynomial.
Terms that need the late x wire (Lx1: bit64 xor bit128) cost 1+lamX, terms that need Ly1 (bit 4) cost 1+lamY."""
import sys, os, math, numpy as np
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
os.environ.setdefault('CLASS_CODES','/work/classiq/artifacts/185/class_codes.json'); os.environ.setdefault('CLASSIQ_ROOT','/work/classiq')
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
from kgenco import build_F, CH, check
n=int(sys.argv[1]); seed=int(sys.argv[2]); lx=float(sys.argv[3]); ly=float(sys.argv[4]); pref=sys.argv[5] if len(sys.argv)>5 else 'cw'
m=np.arange(256); needX=(((m>>6)^(m>>7))&1).astype(float); needY=((m>>2)&1).astype(float)
pen=1+lx*needX+ly*needY
def solve(rng, rounds=12, jit=0.4):
    F,known=build_F(); R=np.where(known)[0]; U=np.where(~known)[0]; N=256
    r0=CH[:,R]@F[R]/N; XU=CH[:,U]/N; nu=len(U); u=np.zeros(nu)
    w=pen*(np.ones(N)+jit*rng.random(N)); w[0]=0; best=None
    for it in range(rounds):
        base=r0+XU@u; nn=np.round(base)
        c=np.concatenate([np.zeros(nu),w])
        A=np.vstack([np.hstack([XU,-np.eye(N)]),np.hstack([-XU,-np.eye(N)])])
        bb=np.concatenate([-(base-nn),(base-nn)])
        res=linprog(c,A_ub=csr_matrix(A),b_ub=bb,bounds=[(None,None)]*nu+[(0,None)]*N,method='highs')
        if not res.success: break
        u=u+res.x[:nu]; b=r0+XU@u; d=b-np.round(b); d[0]=0
        nz=np.abs(d)>1e-7; score=np.sum(pen[nz])
        if best is None or score<best[0]: best=(score,u.copy())
        w=pen/(np.abs(d)+1e-3); w[0]=0
    if best is None: return None
    b=r0+XU@best[1]; frac=b-np.round(b); frac[0]=0; frac[np.abs(frac)<1e-9]=0
    return frac
F,known=build_F(); print('unknown entries',int(np.sum(~known)))
rng=np.random.default_rng(seed); seen=set()
for t in range(n):
    frac=solve(rng)
    if frac is None: continue
    if check(frac)>1e-9: print('BAD'); continue
    nz=np.nonzero(np.abs(frac)>1e-9)[0]; key=tuple(nz)
    if key in seen: continue
    seen.add(key)
    nx=int(needX[nz].sum()); ny=int(needY[nz].sum())
    tag=f'{pref}_{seed}_{t}'; np.save(f'/work/k/cow/{tag}.npy',frac*math.pi)
    print(tag,'terms',len(nz),'needLx1',nx,'needLy1',ny,flush=True)
