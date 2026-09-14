"""Modulo-2pi cube/nullspace moves from the new 63-term phase lift."""
import argparse,json,math
from pathlib import Path
import numpy as np
from depth_parity_network import walsh
from post258_two_stage_anf import decode
p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--steps',type=int,default=1200);a=p.parse_args();out=a.outdir;assert not out.exists();out.mkdir(parents=True)
r=json.loads(Path('artifacts/193/kernel_recipe.json').read_text());c=r['class_codes'];y,x=decode(c['ylab']),decode(c['xlab']);yr={a[0]|b<<1 for a,b in y.items()};xr={a[0]|b<<1 for a,b in x.items()};care=np.array([y|x<<4 for y in yr for x in xr])
start=np.rint(32*np.array(r['co'])).astype(int)%32;start[0]=0
moves=[np.rint(64*walsh([int(m&~w==0) for w in range(256)])).astype(int) for m in range(1,256) if m.bit_count()<=6]
for side,missing in [(0,set(range(16))-yr),(1,set(range(16))-xr)]:
 for value in missing:
  for mask in range(16):
   vec=[int(w>>(4*side)&15==value)*(-1)**((mask&(w>>(4*(1-side))&15)).bit_count()%2) for w in range(256)]
   moves.append(np.rint(16*walsh(vec)).astype(int))
moves=np.array(moves);moves[:,0]=0;moves=np.unique(np.concatenate([moves,-moves,2*moves,-2*moves,4*moves,8*moves])%32,axis=0)
rng=np.random.default_rng(193);cur=start.copy();best=63;rows=[];pool={tuple(start):start.copy()}
for step in range(a.steps):
 if step%150==0:
  cur=list(pool.values())[int(rng.integers(len(pool)))].copy()
  for _ in range(2):cur=(cur+moves[int(rng.integers(len(moves)))])%32
 nxt=(cur[None,:]+moves)%32;score=np.count_nonzero(nxt,axis=1);idx=int(rng.choice(np.flatnonzero(score==score.min())));old=np.count_nonzero(cur);temp=.05+1.5*(1-step%150/150)
 if score[idx]<=old or rng.random()<math.exp(min(0,(old-score[idx])/temp)):cur=nxt[idx]
 count=int(np.count_nonzero(cur))
 if count<=best and tuple(cur) not in pool:
  diff=np.rint(walsh((cur-start).astype(float))*256).astype(int);assert np.all((diff[care]-diff[care[0]])%64==0)
  pool[tuple(cur)]=cur.copy()
  if count<best:
   best=count;print('SUPPORT',best,'step',step,flush=True)
   recipe=dict(r,co=(np.where(cur>16,cur-32,cur)/32).tolist());recipe.pop('sha256',None);(out/f'phase_{count}.json').write_text(json.dumps(recipe,indent=2))
 if step%200==0:print('step',step,'best',best,flush=True)
(out/'report.json').write_text(json.dumps(dict(steps=a.steps,moves=len(moves),best_support=best,unique_equal_or_better=len(pool)),indent=2))
