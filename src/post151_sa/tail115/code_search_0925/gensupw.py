"""gensupw.py side cols gamma n seed outprefix : loader support frames where conditioned (L-dependent) atoms cost 1+gamma.
Fewer L-dependent rotations = less work after Lx0 closes."""
import sys, os, pickle, numpy as np
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
os.environ.setdefault('CLASS_CODES','/work/classiq/artifacts/185/class_codes.json'); os.environ.setdefault('CLASSIQ_ROOT','/work/classiq')
import gensup as G
from condlp import atoms_for
from codes import xcode, ycode, bits
from mkD3 import dump
side=sys.argv[1]; cols=tuple(int(c) for c in sys.argv[2].split(',')); gam=float(sys.argv[3]); n=int(sys.argv[4]); seed=int(sys.argv[5]); pref=sys.argv[6]
cond={0:[],1:[0],2:[0]}
def build(rng,jit=0.35):
    code = xcode if side=='x' else ycode
    B=bits(code)
    Bn=np.array([sum(B[i] for i in range(3) if cols[j]>>i&1)%2 for j in range(3)])
    newcode=[int(Bn[0][v]|(Bn[1][v]<<1)|(Bn[2][v]<<2)) for v in range(64)]
    targets={}
    for i in range(3):
        keys,A=atoms_for(Bn,cond[i])
        geo=np.array([1.0 if len(k[1]) else 0.0 for k in keys])
        r=G.sparse_rep_r(np.pi*Bn[i].astype(float),A,rng,jit=jit,geo=geo,gam=gam)
        if r is None: return None
        sup,sol=r; par={}
        for k,coef in zip(sup,sol):
            s,sub=keys[k]; mask=(1<<(6+i))|s
            for j in sub: mask|=1<<(6+j)
            par[mask]=par.get(mask,0.0)+coef
        targets[i]={m:a for m,a in par.items() if abs(a)>1e-12}
    Minv={}
    for i in range(3):
        for combo in range(1,8):
            v=0
            for j in range(3):
                if combo>>j&1: v^=cols[j]
            if v==(1<<i): Minv[i]=combo
    req=[0x30 if side=='x' else 0x20]+[sum(1<<(6+j) for j in range(3) if Minv[i]>>j&1) for i in range(3)]
    return dict(side=side,cols=cols,cond=cond,targets=targets,gates=[],fix=[],req=req,al=[set(range(9))]*4,newcode=newcode,depth=None,placed=False)
rng=np.random.default_rng(seed); seen=set()
for t in range(n):
    D=build(rng)
    if D is None: continue
    key=tuple(sorted(m for i in range(3) for m in D['targets'][i]))
    if key in seen: continue
    seen.add(key)
    sz=[len(D['targets'][i]) for i in range(3)]; nL=[sum(1 for m in D['targets'][i] if m&64) if i>0 else 0 for i in range(3)]
    tag=f'{pref}_{t}'; dump(D,tag)
    print(tag,'sizes',sz,'total',sum(sz),'Ldep',nL,'post',sum(nL),flush=True)
