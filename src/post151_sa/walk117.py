"""Neutral/uphill whole-network rewrite search after the exhaustive one-move screen."""
import argparse,json,time,random,math
from pathlib import Path
from rewrite117 import moves,optimized,score,graph,scheduled
from postopt import parse_ops,fuse,write
from smilp import solve
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('outdir');p.add_argument('--seconds',type=float,default=150);p.add_argument('--seed',type=int,default=117);a=p.parse_args()
out=Path(a.outdir);out.mkdir(exist_ok=True);base=fuse(parse_ops(a.source));bs=score(base);rng=random.Random(a.seed);cur=base;cs=bs;ms=moves(cur);pool=[];seen=set();history=[];start=time.monotonic();trials=accepted=0
while time.monotonic()-start<a.seconds:
 trials+=1;m=rng.choice(ms);cand,sc=optimized(cur,m,2)
 delta=(sc[0]-cs[0])+.006*(sc[1]-cs[1])
 if sc[0]<=120 and sum(g[0]=='cx' for g in cand)<=630 and (delta<=0 or rng.random()<math.exp(-delta/.3)):
  cur,cs=cand,sc;ms=moves(cur);accepted+=1
  if sc[0]<=117:
   key=tuple((o[0],o[1]) for o in cur)
   if key not in seen:
    seen.add(key);pool.append((sc,trials,cur));pool.sort(key=lambda x:x[:2]);pool=pool[:20]
   if sc[0]<117:
    f=out/f'improve_{trials}_d{sc[0]}.qasm';write(cur,f);print('IMPROVED',f,sc,flush=True);break
 if trials%100==0:print(trials,'accept',accepted,'cur',cs,'best',pool[0][0] if pool else bs,flush=True)
 if trials%160==0:
  if pool and rng.random()<.6:cs,_,cur=rng.choice(pool[:8])
  else:cur,cs=base,bs
  ms=moves(cur)
rows=[]
for sc,k,ops in pool:
 f=out/f'candidate_{k}_d{sc[0]}.qasm';write(ops,f);r=dict(score=sc,trial=k,path=str(f));exact=solve(ops,116,15,False);r['found116']=exact is not None
 if exact is not None:write(fuse(exact),out/f'exact_{k}_d116.qasm');print('EXACT SUCCESS',k,flush=True)
 rows.append(r)
(out/'report.json').write_text(json.dumps(dict(trials=trials,accepted=accepted,seconds=time.monotonic()-start,retained=rows),indent=2));print('DONE',trials,accepted,flush=True)
