"""labeval.py: loader-frame cost of a class labeling (conditional-loader architecture)."""
import os, sys, time, itertools, numpy as np
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
os.environ.setdefault('CLASS_CODES','/work/classiq/artifacts/185/class_codes.json'); os.environ.setdefault('CLASSIQ_ROOT','/work/classiq')
from codes import COLCLS, ROWCLS, XL, YL, H
from condlp import atoms_for
import gensup as G
MASK={'x':48,'y':32}; CLS={'x':COLCLS,'y':ROWCLS}
def keys(side): return sorted({(bin(v&MASK[side]).count('1')%2, CLS[side][v]) for v in range(64)})
def code_of(side,lab): return [lab[(bin(v&MASK[side]).count('1')%2, CLS[side][v])] for v in range(64)]
def walsh_support(f):
    # exact number of parity terms representing pi*f (f 0/1 over 6 bits), constant excluded
    s=H@(1-2*np.asarray(f,float)); return int(np.sum(np.abs(s[1:])>1e-9))
def cond_cost(fb, f0, rng, reps=2):
    Bn=np.array([f0, fb, fb])
    keys_,A=atoms_for(Bn,[0])
    best=None
    for r in range(reps):
        out=G.sparse_rep_r(np.pi*fb.astype(float),A,rng,jit=0.35)
        if out is None: continue
        sup,sol=out
        nL=sum(1 for k in sup if len(keys_[k][1])); n=len(sup)
        if best is None or n<best[0]: best=(n,nL)
    return best
def frame_cost(side, lab, rng, reps=2):
    code=code_of(side,lab); B=np.array([[(c>>b)&1 for c in code] for b in range(3)])
    combos={m: np.array(sum(B[i] for i in range(3) if m>>i&1)%2) for m in range(1,8)}
    res=[]
    for m0 in range(1,8):
        t0=walsh_support(combos[m0])
        cc={}
        for m in range(1,8):
            if m==m0: continue
            cc[m]=cond_cost(combos[m],combos[m0],rng,reps)
        # choose m1,m2 with {m0,m1,m2} independent minimizing post (L-dep) then total
        for m1,m2 in itertools.combinations(cc,2):
            if m1^m2==m0 or m1^m2^m0==0: continue
            if m1^m2 in (0,): continue
            if (m0^m1)==m2: continue
            n1,l1=cc[m1]; n2,l2=cc[m2]
            res.append(dict(m=(m0,m1,m2),t0=t0,t1=n1,t2=n2,L=l1+l2,pre=t0+(n1-l1)+(n2-l2),total=t0+n1+n2))
    return res
if __name__=='__main__':
    rng=np.random.default_rng(0)
    for side,lab in (('x',XL),('y',YL)):
        t=time.time(); r=frame_cost(side,lab,rng)
        r.sort(key=lambda d:(d['L'],d['total']))
        print(side,'time %.1fs'%(time.time()-t))
        for d in r[:6]: print('  ',d)
