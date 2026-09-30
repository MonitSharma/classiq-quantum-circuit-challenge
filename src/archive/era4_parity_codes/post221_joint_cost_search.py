"""Co-design code tables and kernel using both Walsh costs, with nonlinear label moves."""
import argparse,json,math,random,time
from pathlib import Path
import numpy as np
from post258_raw_parity_codes import cells,poly
from post258_two_stage_anf import ORDER,encode,decode
from post258_encoder_lifts import H
from depth_parity_network import walsh
import two_stage_oracle as ts

def run(outdir,steps,seed):
 assert not outdir.exists();outdir.mkdir(parents=True);rng=random.Random(seed);base=json.loads(Path('artifacts/221/class_codes.json').read_text());labs=[decode(base['ylab']),decode(base['xlab'])];cc=[cells(ts.ROWCLS,32),cells(ts.COLCLS,48)]
 spectra=np.array([256*walsh([int(m&~w==0) for w in range(256)]) for m in ORDER],int)
 def evaluate():
  totals=[]
  for lab,cells_ in zip(labs,cc):
   codes=np.zeros(64,dtype=int)
   for k,vs in cells_.items():codes[vs]=lab[k]
   sp=np.array([((codes>>b)&1)@H for b in range(3)]);totals.append(int(np.count_nonzero(sp)))
  sol=poly(*labs,*cc);ids=[i for i in range(256) if sol>>i&1];co=spectra[ids].sum(axis=0)%256;co[0]=0
  count=int(np.count_nonzero(co));degree=max(ORDER[i].bit_count() for i in ids)
  cost=.40*max(totals)+.6*count+3*max(0,degree-5)
  return cost,totals,count,[ORDER[i] for i in ids]
 cur,totals,count,terms=evaluate();best=cur;history=[];seen=set();start=time.monotonic()
 for step in range(steps):
  side=rng.randrange(2);lab=labs[side];prev=lab.copy();keys=list(lab)
  if rng.random()<.45:
   target=rng.randrange(3);controls=[b for b in range(3) if b!=target];kind=rng.randrange(3);half=rng.choice([None,0,1])
   for k in keys:
    if half is not None and k[0]!=half:continue
    a=lab[k]>>controls[0]&1;b=lab[k]>>controls[1]&1
    lab[k]^=(1 if kind==0 else a if kind==1 else a*b)<<target
  else:
   k=rng.choice(keys);v=rng.randrange(8);other=next((o for o in keys if o[0]==k[0] and lab[o]==v),None);old=lab[k];lab[k]=v
   if other is not None:lab[other]=old
  val,totals,count,terms=evaluate();temp=.15+4*(1-(step%2000)/2000)
  if val<=cur or rng.random()<math.exp(min(0,(cur-val)/temp)):cur=val
  else:lab.clear();lab.update(prev);continue
  key=tuple(tuple(l.values()) for l in labs)
  if cur<best+.5 and key not in seen:
   seen.add(key);row=dict(step=step,seed=seed,cost=cur,supports=totals,kernel_support=count,ymask=32,xmask=48,ylab=encode(labs[0]),xlab=encode(labs[1]),terms=terms);history.append(row)
   if cur<best:best=cur;print('best',step,round(cur,2),totals,count,flush=True)
 history.sort(key=lambda r:r['cost']);chosen=history[:30]
 for i,r in enumerate(chosen):(outdir/f'candidate_{i}.json').write_text(json.dumps(r,indent=2)+'\n')
 (outdir/'report.json').write_text(json.dumps(dict(steps=steps,seed=seed,seconds=time.monotonic()-start,rows=chosen),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--steps',type=int,default=20000);p.add_argument('--seed',type=int,default=1);a=p.parse_args();run(a.outdir,a.steps,a.seed)
