"""Screen mixed x/y six-wire partitions after cheap reversible preprocessing.

Counts are necessary descriptor capacities, not native oracle depths. This
screen permits arbitrary functions of each half and does not synthesize them.
"""
import argparse,itertools,json,time
from pathlib import Path
import numpy as np
from two_stage_oracle import logo

def run(out):
 assert not out.exists();out.mkdir(parents=True)
 v=np.arange(4096);truth=np.array([logo(int(w)&63,int(w)>>6) for w in v],np.uint8)
 partitions=[]
 for left in itertools.combinations(range(12),6):
  if 0 not in left:continue
  right=tuple(b for b in range(12) if b not in left)
  a=sum((v>>bit&1)<<i for i,bit in enumerate(left));b=sum((v>>bit&1)<<i for i,bit in enumerate(right));index=np.argsort(a*64+b)
  partitions.append((left,right,index))
 transforms=[('identity',())]
 for a in range(6):
  for b in range(6,12):transforms.extend([('cx',(a,b)),('cx',(b,a))])
 for a in range(6):
  for b in range(6,12):
   for t in range(12):
    if t not in (a,b):transforms.append(('ccx',(a,b,t)))
 records=[];witnesses=[];start=time.time()
 for number,(kind,gate) in enumerate(transforms):
  if kind=='identity':perm=v
  elif kind=='cx':a,b=gate;perm=v^((v>>a&1)<<b)
  else:a,b,t=gate;perm=v^(((v>>a&1)&(v>>b&1))<<t)
  # Each chosen gate is an involution: evaluate f(pre^{-1}(z)).
  f=truth[perm];best=None
  for left,right,index in partitions:
   table=f[index].reshape(64,64)
   lc=len(np.unique(np.packbits(table,axis=1),axis=0));rc=len(np.unique(np.packbits(table.T,axis=1),axis=0))
   score=(max(lc,rc),lc*rc)
   if best is None or score<best[0]:best=(score,left,right,lc,rc)
   if lc<=16 and rc<=16:
    witnesses.append(dict(kind=kind,gate=gate,left=left,right=right,classes=[lc,rc]))
  records.append(dict(kind=kind,gate=gate,left=best[1],right=best[2],classes=[best[3],best[4]]))
  if number%50==0:print('transform',number,'of',len(transforms),'valid partitions',len(witnesses),'elapsed',round(time.time()-start),flush=True)
 (out/'report.json').write_text(json.dumps(dict(transforms=len(transforms),partitions=len(partitions),pairs_checked=len(transforms)*len(partitions),records=records,witnesses=witnesses),indent=2))
 print('complete witnesses',len(witnesses),'mixed',sum(w['left']!=list(range(6)) and tuple(w['left'])!=tuple(range(6)) for w in witnesses),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();run(a.outdir)
