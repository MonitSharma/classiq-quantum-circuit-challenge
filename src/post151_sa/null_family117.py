"""Exact small-support reachable-code null phases, lifted across the other axis."""
import os,json,math,itertools
from pathlib import Path
import numpy as np
from kgenco import build_F,CH
from kdrv import CO
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/phase_network117_20260922/null_family';out.mkdir(exist_ok=True)
F,known=build_F();grid=known.reshape(16,16);base=np.rint(CO/math.pi*32).astype(int);seen=set();retained=[];hist={}
for side,valid in [('x',grid.any(axis=1)),('y',grid.any(axis=0))]:
 missing=np.flatnonzero(~valid)
 for subset in itertools.chain(((int(a),) for a in missing),itertools.combinations(map(int,missing),2),itertools.combinations(map(int,missing),3)):
  for signs in itertools.product([-1,1],repeat=len(subset)-1):
   signs=(1,)+signs
   v=np.array([sum(s*((-1)**((m&z).bit_count())) for z,s in zip(subset,signs)) for m in range(16)])
   g=math.gcd(*map(abs,v));v//=g
   for other in range(16):
    vv=np.zeros(256,dtype=int)
    for m,c in enumerate(v):vv[(m<<4|other) if side=='x' else (other<<4|m)]=c
    assert np.max(abs((CH.T@vv)[known]))==0
    alphas={-int(base[m])//int(vv[m]) for m in range(1,256) if vv[m] and base[m] and base[m]%vv[m]==0}
    for alpha in alphas:
     if alpha==0:continue
     a=(base+alpha*vv+16)%32-16;a[0]=0;support=tuple(np.flatnonzero(a));n=len(support);hist[n]=hist.get(n,0)+1
     key=tuple(map(int,a))
     if n>64 or key in seen:continue
     seen.add(key);idx=len(retained);np.save(out/f'co_{idx}.npy',a/32*math.pi)
     added=sorted(set(support)-set(np.flatnonzero(base)));removed=sorted(set(np.flatnonzero(base))-set(support)-{0})
     r=dict(index=idx,terms=n,side=side,missing=subset,signs=signs,other=other,alpha=alpha,added=list(map(int,added)),removed=list(map(int,removed)));retained.append(r)
print('hist',hist,flush=True);print('retained',len(retained),flush=True)
for r in retained:print(r,flush=True)
(out/'report.json').write_text(json.dumps(retained,indent=2))
