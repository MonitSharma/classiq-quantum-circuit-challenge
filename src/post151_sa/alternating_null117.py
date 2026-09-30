"""Couple both axes' exact unreachable-code freedoms; preserve the phase specification."""
import os,math,json,itertools
from pathlib import Path
import numpy as np
from kdrv import CO
from kgenco import build_F,CH
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/phase_network117_20260922/alternating';out.mkdir(exist_ok=True)
F,known=build_F();grid=known.reshape(16,16);base=np.rint(CO/math.pi*32).astype(int);base[0]=0
D={}
for side,valid in [('x',grid.any(1)),('y',grid.any(0))]:
 missing=np.flatnonzero(~valid);basis=np.array([[(-1)**((m&int(v)).bit_count()) for m in range(16)] for v in missing]);xyz=np.array(list(itertools.product(range(-32,32),repeat=len(missing))));xyz=xyz[xyz.sum(1)%2==0];D[side]=np.unique((xyz@basis//2)%32,axis=0)
 print(side,'null choices',len(D[side]),flush=True)

def step(coeff,side,seed):
 rng=np.random.default_rng(seed);mat=coeff.reshape(16,16).copy();blocks=mat.T if side=='x' else mat
 for j,b in enumerate(blocks):
  candidates=(b+D[side]+16)%32-16
  if j==0:candidates[:,0]=0
  cnt=np.count_nonzero(candidates,axis=1);ix=np.flatnonzero(cnt==cnt.min());i=int(rng.choice(ix));blocks[j]=candidates[i]
 return mat.ravel().copy()

blocks=json.loads((ROOT/'artifacts/phase_network117_20260922/block_null/blocks.json').read_text());seen=set();records=[];best=63
combos=list(itertools.product(range(3),range(2),range(4)))
for k,choice in enumerate(combos):
 arr=np.array([r[0]['co'] for r in blocks]);arr[0]=blocks[0][choice[0]]['co'];arr[6]=blocks[6][choice[1]]['co'];arr[12]=blocks[12][choice[2]]['co'];a=arr.ravel()
 for it in range(4):
  side='x' if it%2==0 else 'y';a=step(a,side,1000*k+it);n=np.count_nonzero(a);key=tuple(map(int,a))
  if n<=63 and key not in seen:
   seen.add(key);idx=len(records);np.save(out/f'co_{idx}.npy',a/32*math.pi);d=(CH.T@(a-base)/32)[known];d-=d[0];assert np.max(abs((d+1)%2-1))<1e-10
   r=dict(index=idx,start=choice,step=it,terms=int(n));records.append(r)
  if n<best:best=n;print('NEW SUPPORT',n,k,it,flush=True)
 print('start',choice,'terms',np.count_nonzero(a),'best',best,'retained',len(records),flush=True)
(out/'report.json').write_text(json.dumps(records,indent=2))
