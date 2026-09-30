"""Reweighted-L1 LP over reachable-code phase freedom, penalising terms on late coordinates."""
import sys, os, numpy as np, math
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
os.environ.setdefault('CLASS_CODES','/work/classiq/artifacts/185/class_codes.json'); os.environ.setdefault('CLASSIQ_ROOT','/work/classiq')
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
from kgenco import build_F, CH
F,known=build_F(); R=np.where(known)[0]; U=np.where(~known)[0]
ST=[2,8,1,4,32,64,192,16]; LATE=[3,5,6,7]   # coordinate indices: Ly1, Lx1, x12, px
coord={}
for s in range(256):
    v=0
    for k in range(8):
        if s>>k&1: v^=ST[k]
    coord[v]=s
def late(m): return any(coord[m]>>k&1 for k in LATE)
def nlate(m): return sum(coord[m]>>k&1 for k in LATE)
PI=math.pi
co=np.load(os.environ.get('CO0','/work/classiq/artifacts/116/recipes/kernel_co.npy'))
def stats(c):
    fr=c/PI-np.round(c/PI); fr[0]=0; nz=np.abs(fr)>1e-7
    return int(nz.sum()), int(sum(1 for m in range(256) if nz[m] and late(m)))
XU=CH[:,U]/256.0
def run(wl=1.0, we=0.02, wm=0.0, rounds=12, seed=0, jit=0.3):
    rng=np.random.default_rng(seed); nu=len(U); N=256
    w=np.array([ (wl*(1+wm*(nlate(m)-1)) if late(m) else we) for m in range(N)])*(1+jit*rng.random(N)); w[0]=0
    u=np.zeros(nu); best=None
    A=csr_matrix(np.vstack([np.hstack([XU,-np.eye(N)]),np.hstack([-XU,-np.eye(N)])]))
    for it in range(rounds):
        base=co/PI+XU@u; n=np.round(base)
        c=np.concatenate([np.zeros(nu),w])
        bb=np.concatenate([-(base-n),(base-n)])
        res=linprog(c,A_ub=A,b_ub=bb,bounds=[(None,None)]*nu+[(0,None)]*N,method='highs')
        if not res.success: break
        u=u+res.x[:nu]
        cc=(co/PI+XU@u)*PI; k,kl=stats(cc)
        key=(kl,k)
        if best is None or key<best[0]: best=(key,cc.copy())
        d=cc/PI-np.round(cc/PI); d[0]=0
        w=np.array([ (wl*(1+wm*(nlate(m)-1)) if late(m) else we) for m in range(N)])/(np.abs(d)+1e-3); w[0]=0
    return best
def check(cnew):
    ph0=CH.T@co; ph1=CH.T@cnew; d=(ph1-ph0)[R]; d=d-d[0]
    d=(d+PI)%(2*PI)-PI
    return float(np.max(np.abs(d)))
if __name__=='__main__':
    out=sys.argv[1] if len(sys.argv)>1 else '/work/k/late'
    os.makedirs(out,exist_ok=True); seen=set(); res=[]
    print('base terms,late',stats(co),flush=True)
    for seed in range(int(os.environ.get('NS','20'))):
        for wl,we,wm in [(1,0.02,0),(1,0.1,0),(1,0.02,0.5),(1,0.3,0),(1,0.01,1.0)]:
            b=run(wl,we,wm,seed=seed)
            if b is None: continue
            (kl,k),cc=b
            fr=cc/PI-np.round(cc/PI); fr[0]=0; fr[np.abs(fr)<1e-9]=0
            key=tuple(np.flatnonzero(np.abs(fr)>1e-7))
            if key in seen: continue
            seen.add(key); cst=fr*PI; err=check(cst)
            res.append((kl,k,seed,wl,we,wm,err))
            np.save(f'{out}/late_s{seed}_{wl}_{we}_{wm}_L{kl}_T{k}.npy',cst)
            print('seed',seed,'w',(wl,we,wm),'late',kl,'terms',k,'err %.1e'%err,flush=True)
    res.sort(); print('best',res[:10])
