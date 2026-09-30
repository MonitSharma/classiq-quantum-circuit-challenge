"""Enumerate exact reachable-code phase freedom independently in each x-mask block."""
import os,json,math,itertools
from pathlib import Path
import numpy as np
from kgenco import build_F,CH
from kdrv import CO
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/phase_network117_20260922/block_null';out.mkdir(exist_ok=True)
F,known=build_F();missing=np.flatnonzero(~known.reshape(16,16).any(axis=0));assert len(missing)==3
basis=np.array([[(-1)**((m&int(v)).bit_count()) for m in range(16)] for v in missing],int)
# Half-integer coefficients allow pairwise cancellation of half of the Walsh terms.
xyz=np.array(list(itertools.product(range(-32,32),repeat=3)),int);xyz=xyz[xyz.sum(1)%2==0]
deltas=xyz@basis//2
base=np.rint(CO/math.pi*32).astype(int);base[0]=0;blocks=[]
for other in range(16):
 b=base[other*16:(other+1)*16];allc=(b+deltas+16)%32-16
 if other==0:allc[:,0]=0
 counts=np.count_nonzero(allc,axis=1);mn=int(counts.min());ix=np.flatnonzero(counts==mn);by_support={}
 for i in ix:
  coeff=allc[i];support=tuple(map(int,np.flatnonzero(coeff)));key=support
  # Keep closest representative for a support.
  dist=int(np.sum(np.minimum((coeff-b)%32,(b-coeff)%32)))
  if key not in by_support or dist<by_support[key][0]:by_support[key]=(dist,coeff.copy())
 rows=[]
 for j,(support,(dist,coeff)) in enumerate(sorted(by_support.items())):
  rows.append(dict(support=support,co=coeff.tolist(),distance=dist))
 blocks.append(rows);print('block',other,'base',np.count_nonzero(b),'min',mn,'distinct supports',len(rows),flush=True)
(out/'blocks.json').write_text(json.dumps(blocks,indent=2));print('MIN TOTAL',sum(len(v[0]['support']) for v in blocks),flush=True)
# Construct variants optimising weighted per-y-mask participation, independently per block.
seen=set();rs=[]
weights_list=list(itertools.product([0,1,4],repeat=4))
for weights in weights_list:
 co=[]
 for other,rows in enumerate(blocks):
  def score(r):return (sum(sum(weights[k] for k in range(4) if m>>k&1) for m in r['support']),r['distance'],r['support'])
  winner=min(rows,key=score);co.extend(winner['co'])
 a=np.array(co);key=tuple(co)
 if key in seen:continue
 seen.add(key);idx=len(rs);d=CH.T@(a-base)/32;dd=d[known];dd-=dd[0];assert np.max(abs(np.remainder(dd+1,2)-1))<1e-10
 np.save(out/f'co_{idx}.npy',a/32*math.pi);terms=np.flatnonzero(a);r=dict(index=idx,weights=weights,terms=len(terms),counts=[int(np.count_nonzero(terms&(1<<k))) for k in range(8)]);rs.append(r);print(r,flush=True)
(out/'report.json').write_text(json.dumps(rs,indent=2))
