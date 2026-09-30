"""Search adjacent exact null-phase representations, weighted by physical code basis."""
import os,sys,json,math,random,itertools,time,heapq
from pathlib import Path
import numpy as np
from kgenco import build_F,CH
from kdrv import CO
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/phase_network117_20260922/plateau';out.mkdir(exist_ok=True)
F,known=build_F();grid=known.reshape(16,16);moves=[]
for side,valid in [('x',grid.any(1)),('y',grid.any(0))]:
 missing=np.flatnonzero(~valid)
 for subset in itertools.chain(((int(a),) for a in missing),itertools.combinations(map(int,missing),2),itertools.combinations(map(int,missing),3)):
  for sg in itertools.product([-1,1],repeat=len(subset)-1):
   signs=(1,)+sg;v=np.array([sum(s*((-1)**((m&z).bit_count())) for z,s in zip(subset,signs)) for m in range(16)]);v//=math.gcd(*map(abs,v))
   for other in range(16):
    vv=np.zeros(256,dtype=np.int16)
    for m,c in enumerate(v):vv[(m<<4|other) if side=='x' else (other<<4|m)]=c
    moves.append(vv)
# Add mixed missing-x * missing-y rank-one changes, allowing new coupling between axis blocks.
for x in np.flatnonzero(~grid.any(1)):
 for y in np.flatnonzero(~grid.any(0)):
  vx=np.array([(-1)**((m&int(x)).bit_count()) for m in range(16)]);vy=np.array([(-1)**((m&int(y)).bit_count()) for m in range(16)]);moves.append(np.kron(vx,vy))
M=np.array(moves,dtype=np.int16);assert np.max(abs(CH[:,known].T@M.T))==0
# All canonical masks expressed in the actual code-wire basis.
ST=[2,8,1,4,32,64,192,16];coord={}
for s in range(256):
 v=0
 for k,r in enumerate(ST):
  if s>>k&1:v^=r
 coord[v]=s
bits=np.array([[(coord[m]>>k)&1 for k in range(8)] for m in range(256)],dtype=np.int16)
base=np.rint(CO/math.pi*32).astype(np.int16);base[0]=0;seed=np.rint(np.load(ROOT/'artifacts/116/recipes/kernel_co.npy')/math.pi*32).astype(np.int16);seed[0]=0
weights=np.array([.3,.5,.5,2,.5,2,2,2]);rng=np.random.default_rng(116);records=[];seen={};pool=[seed];bestn=63;start=time.monotonic();scores=[]
for it in range(3000):
 if it<len(pool):a=pool[it]
 else:a=pool[int(rng.integers(len(pool)))]
 # Try all small cancellation-sized amplitudes. Keep sparse neighbours and diversify.
 deltas=np.array([amp*M for amp in [-4,-3,-2,-1,1,2,3,4]],dtype=np.int16).reshape(-1,256)
 trials=(a[None,:]+deltas+16)%32-16;trials[:,0]=0;support=trials!=0;cnt=support.sum(1);valid=np.flatnonzero(cnt<=64)
 if not len(valid):continue
 rank=support[valid]@bits@weights+cnt[valid]*5+rng.random(len(valid))*.2
 order=valid[np.argsort(rank)[:12]]
 for j in order:
  b=trials[j];key=b.tobytes()
  if key in seen:continue
  index=len(pool);seen[key]=index;pool.append(b.copy())
  n=int(cnt[j]);phys=(support[j]@bits).tolist();score=float(n*5+np.dot(phys,weights));scores.append((n,score,index,phys))
  if n<bestn:bestn=n;print('SUPPORT',n,'iteration',it,flush=True)
 if it%100==0:print('iteration',it,'pool',len(pool),'best terms',bestn,'seconds',round(time.monotonic()-start,1),flush=True)
 if len(pool)>10000:break
# Select by physical-weight score and distinct supports, plus one-wire specialisation.
selected=set();support_seen=set()
for sortkey in [lambda s:(s[0],s[1])]+[lambda s,w=w:(s[0],s[3][w],s[1]) for w in [3,5,6,7]]:
 take=0
 for n,score,i,phys in sorted(scores,key=sortkey):
  supp=(pool[i]!=0).tobytes()
  if supp in support_seen:continue
  support_seen.add(supp);selected.add(i);take+=1
  if take>=12:break
for i in sorted(selected):
 b=pool[i];d=(CH.T@(b-base)/32)[known];d-=d[0];assert np.max(abs((d+1)%2-1))<1e-10
 idx=len(records);np.save(out/f'co_{idx}.npy',b/32*math.pi);records.append(dict(index=idx,pool_index=i,terms=int(np.count_nonzero(b)),physical_counts=((b!=0)@bits).tolist()))
(out/'report.json').write_text(json.dumps(dict(iterations=it+1,pool=len(pool),best_terms=bestn,retained=records,seconds=time.monotonic()-start),indent=2));print('DONE',len(records),bestn,flush=True)
