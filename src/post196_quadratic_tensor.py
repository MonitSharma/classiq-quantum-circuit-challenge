"""Loader-free oracle using six pairwise products and local sign bases.
Each four-valued input pair has eight sign characters available after one
relative-phase AND. Invertible four-column bases give exact tensor expansions.
Searches modular phase-equivalent coefficient representations, not approximations.
"""
import argparse,itertools,json,random,math
from pathlib import Path
import numpy as np
from two_stage_oracle import logo

SIG=np.array([[(-1)**((m & (a|(b<<1)|((a&b)<<2))).bit_count()%2) for m in range(8)] for b in range(2) for a in range(2)],float)
BASES=[(0,)+t for t in itertools.combinations(range(1,8),3) if abs(np.linalg.det(SIG[:,(0,)+t]))>.1]
MATS=[SIG[:,b] for b in BASES];INVS=[np.linalg.inv(m) for m in MATS]
TRANS=np.array([[i@m for m in MATS] for i in INVS])
def axis_apply(t,m,axis):return np.moveaxis(np.tensordot(m,t,axes=(1,axis)),0,axis)
def mod(t):return (t+.5)%1-.5

def run(outdir,restarts):
 assert not outdir.exists();outdir.mkdir(parents=True);rng=random.Random(140);best=4097;records=[]
 for restart in range(restarts):
  if restart<8:pairs=[(0,1),(2,3),(4,5),(6,7),(8,9),(10,11)]
  elif restart<16:pairs=[(0,6),(1,7),(2,8),(3,9),(4,10),(5,11)]
  else:
   order=list(range(12));rng.shuffle(order);pairs=list(zip(order[::2],order[1::2]))
  tensor=np.zeros((4,)*6)
  for idx in np.ndindex(tensor.shape):
   w=sum((v&1)<<a|(v>>1)<<b for v,(a,b) in zip(idx,pairs));tensor[idx]=logo(w&63,w>>6)
  choices=[rng.randrange(len(BASES)) for _ in range(6)];co=tensor.copy()
  for axis,b in enumerate(choices):co=axis_apply(co,INVS[b],axis)
  co=mod(co);co[(0,)*6]=0
  for sweep in range(12):
   changed=False;axes=list(range(6));rng.shuffle(axes)
   for axis in axes:
    options=[]
    for b in range(len(BASES)):
     cand=mod(axis_apply(co,TRANS[b,choices[axis]],axis));cand[(0,)*6]=0
     options.append((np.count_nonzero(cand),float(np.abs(cand).sum()),rng.random(),b,cand))
    score,_,_,b,cand=min(options,key=lambda v:v[:3])
    if score<=np.count_nonzero(co):
     changed |= b!=choices[axis];choices[axis]=b;co=cand
   if not changed:break
  support=int(np.count_nonzero(co))
  if support<best:
   best=support;recon=co.copy()
   for axis,b in enumerate(choices):recon=axis_apply(recon,MATS[b],axis)
   diff=recon-tensor;err=float(np.max(abs(((diff-diff.flat[0]+1)%2)-1)));assert err<1e-10,err
   terms=[]
   for idx in zip(*np.nonzero(co)):
    mask=0
    for axis,(a,b) in enumerate(pairs):
     local=BASES[choices[axis]][idx[axis]]
     mask|=(local&1)<<a|((local>>1)&1)<<b|((local>>2)&1)<<(12+axis)
    terms.append([mask,float(co[idx])])
   row=dict(restart=restart,pairs=pairs,bases=[BASES[b] for b in choices],support=support,phase_error=err,terms=terms);records.append(row)
   (outdir/'best.json').write_text(json.dumps(row,indent=2));print('quadratic terms',support,'restart',restart,flush=True)
 (outdir/'report.json').write_text(json.dumps(dict(restarts=restarts,best=best,records=records),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--restarts',type=int,default=80);a=p.parse_args();run(a.outdir,a.restarts)
