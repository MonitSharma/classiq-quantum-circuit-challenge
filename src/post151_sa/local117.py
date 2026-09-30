"""Exact three-wire phase-network replacements, with full-context scoring."""
import argparse,json,time,itertools,math,random
from collections import deque
from functools import lru_cache
from pathlib import Path
import numpy as np
from postopt import parse_ops,fuse,write,depth
from rewrite117 import score,graph,scheduled
from canc import simplify
from smilp import solve

@lru_cache(maxsize=8192)
def shortest(goal,required,variant):
 start=((1,2,4),0);queue=deque([start]);par={start:None};pairs=list(itertools.permutations(range(3),2));rng=random.Random(variant);rng.shuffle(pairs)
 while queue:
  state=queue.popleft();basis,done=state
  if state==(goal,required):
   layers=[]
   while par[state] is not None:prev,layer=par[state];layers.append(layer);state=prev
   return list(reversed(layers))
  avail=[w for w in range(3) if (required>>basis[w]&1) and not(done>>basis[w]&1)]
  choices=[(None,tuple(avail))] if avail else []
  choices += [((a,b),(3-a-b,) if 3-a-b in avail else ()) for a,b in pairs]
  for pair,ws in choices:
   dd=done
   for w in ws:dd|=1<<basis[w]
   bb=list(basis)
   if pair:a,b=pair;bb[b]^=bb[a]
   nxt=tuple(bb),dd
   if nxt not in par:par[nxt]=(state,(pair,ws));queue.append(nxt)
 raise RuntimeError('unreachable')

def collect(ops,anchor,wires):
 allowed=set(wires);blocked=set();selected=[]
 for i in range(anchor,min(len(ops),anchor+240)):
  g=ops[i];ws=set(g[1])
  if not ws&allowed:continue
  diag=g[0]=='cx' or abs(g[2][0,1])+abs(g[2][1,0])<1e-12
  if ws<=allowed and not ws&blocked and diag:selected.append(i)
  else:blocked.update(ws&allowed)
  if blocked>=allowed:break
 return selected

def synth(ops,selected,wires,variant):
 ids={w:i for i,w in enumerate(wires)};basis=[1,2,4];angles={}
 for k in selected:
  g=ops[k]
  if g[0]=='cx':basis[ids[g[1][1]]]^=basis[ids[g[1][0]]]
  else:
   m=basis[ids[g[1][0]]];angles[m]=angles.get(m,0)+np.angle(g[2][1,1]/g[2][0,0])
 angles={m:(v+math.pi)%(2*math.pi)-math.pi for m,v in angles.items()};angles={m:v for m,v in angles.items() if abs(v)>1e-10}
 goal=tuple(basis);layers=shortest(goal,sum(1<<m for m in angles),variant);basis=[1,2,4];replacement=[]
 for pair,ws in layers:
  for w in ws:replacement.append(('u3',(wires[w],),np.diag([1,np.exp(1j*angles[basis[w]])])))
  if pair:a,b=pair;replacement.append(('cx',(wires[a],wires[b]),None));basis[b]^=basis[a]
 assert tuple(basis)==goal
 return replacement

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('outdir');p.add_argument('--seconds',type=int,default=150);a=p.parse_args();out=Path(a.outdir);out.mkdir(exist_ok=True)
 base=fuse(parse_ops(a.source));ops=base;best=score(base);rng=random.Random(117);start=time.monotonic();seen=set();history=[];pool=[];trial=attempts=0
 while time.monotonic()-start<a.seconds:
  trial+=1;cx=[i for i,g in enumerate(ops) if g[0]=='cx'];anchor=rng.choice(cx);ws=set(ops[anchor][1]);near=sorted({w for o in ops[anchor:anchor+75] for w in o[1]}-ws)
  if not near:continue
  wires=tuple(sorted(ws|{rng.choice(near)}));sel=collect(ops,anchor,wires)
  if len(sel)<4:continue
  key=(tuple(sel),wires)
  if key in seen:continue
  seen.add(key);old=[ops[k] for k in sel];repl=synth(ops,sel,wires,trial%3)
  if score(repl)>=score(old):continue
  attempts+=1;ss=set(sel);cand=ops[:sel[0]]+repl+[o for k,o in enumerate(ops) if k>=sel[0] and k not in ss];cand=fuse(simplify(cand,False));sc=score(cand)
  if sc[0]<=118:
   original=cand;g=graph(original)
   for seed in range(2):
    cc=scheduled(original,g,seed);s=score(cc)
    if s<sc:cand,sc=cc,s
  pool.append((sc,trial,cand));pool.sort(key=lambda v:v[:2]);pool=pool[:12]
  if sc<best:
   ops,best=cand,sc;history.append(dict(trial=trial,score=sc,wires=wires,selected=sel));seen.clear();path=out/f'improved_{trial}_d{sc[0]}.qasm';write(cand,path);print('IMPROVED',path,sc,flush=True)
   if sc[0]<117:break
  if attempts%100==0:print('trial',trial,'replacements',attempts,'best',best,flush=True)
 rows=[]
 for sc,k,cand in pool:
  path=out/f'candidate_{k}_d{sc[0]}.qasm';write(cand,path);row=dict(score=sc,path=str(path));ex=solve(cand,116,10,False);row['found116']=ex is not None
  if ex is not None:write(fuse(ex),out/f'exact_{k}_116.qasm');print('EXACT SUCCESS',k,flush=True)
  rows.append(row)
 (out/'report.json').write_text(json.dumps(dict(trials=trial,replacements=attempts,best=best,history=history,retained=rows,seconds=time.monotonic()-start),indent=2));print('DONE',trial,attempts,best,flush=True)
