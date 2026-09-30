"""Search modular, rather than real-null, freedoms in each 4-bit Fourier block."""
import os,json,math,random,itertools,time
from pathlib import Path
import numpy as np
from kgenco import build_F,CH
from kdrv import CO
from modsupport117 import solve_mod
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/phase_network117_20260922/modular_blocks';out.mkdir(exist_ok=True)
F,known=build_F();valid=known.reshape(16,16).any(0);H=CH[:16,:16].astype(int)[:,valid].T
base=np.rint(CO/math.pi*32).astype(int);base[0]=0;rng=random.Random(117);blocks=[];start=time.monotonic()
for x in range(16):
 b=base[x*16:(x+1)*16];B=H@b
 if x==0:A=(H-H[0])%64;B=(B-B[0])%64;free=np.zeros((len(B),0),int);universe=list(range(1,16))
 else:A=H;free=np.full((len(B),1),32,dtype=int);universe=list(range(16))
 cache={}
 def feasible(support,solution=False):
  key=tuple(sorted(support))
  if key not in cache:
   mat=np.column_stack([A[:,key],free]);v=solve_mod(mat,B,64)
   if v is not None:assert np.all((mat@v-B)%64==0)
   cache[key]=None if v is None else v[:len(key)]
  return cache[key]
 mandatory={m for m in universe if feasible([n for n in universe if n!=m]) is None}
 mincount=int(np.count_nonzero(b));best=[];seen=set()
 for seed in range(140):
  support=universe.copy();order=list(set(universe)-mandatory);rng.shuffle(order)
  for m in order:
   trial=[n for n in support if n!=m]
   if feasible(trial) is not None:support=trial
  v=feasible(support);a=np.zeros(16,dtype=int);a[support]=v;a=(a+16)%32-16
  if x==0:a[0]=0
  cnt=int(np.count_nonzero(a));key=tuple(a)
  if cnt<mincount:mincount=cnt;best=[];seen=set()
  if cnt==mincount and key not in seen:seen.add(key);best.append(a.tolist())
 if not best:best=[b.tolist()]
 blocks.append(best);print('block',x,'base',np.count_nonzero(b),'min',mincount,'mandatory',sorted(mandatory),'choices',len(best),'systems',len(cache),'sec',round(time.monotonic()-start,1),flush=True)
(out/'blocks.json').write_text(json.dumps(blocks,indent=2));print('minimum',sum(np.count_nonzero(b[0]) for b in blocks),flush=True)
seen=set();rs=[]
for seed in range(32):
 a=np.array(list(itertools.chain.from_iterable(rng.choice(b) for b in blocks)));key=tuple(a)
 if key in seen:continue
 seen.add(key);d=(CH.T@(a-base)/32)[known];d-=d[0];assert np.max(abs((d+1)%2-1))<1e-10
 idx=len(rs);np.save(out/f'co_{idx}.npy',a/32*math.pi);rs.append(dict(index=idx,terms=int(np.count_nonzero(a))))
(out/'report.json').write_text(json.dumps(rs,indent=2))
