"""Apply an exact CNOT bridge to a loader and its mirrored inverse together."""
import os,pickle,json,time
from pathlib import Path
import numpy as np
from build import loader_ops
from kdrv import full_gates,XW,YW,PHYS
from rewrite117 import moves,rewrite,score,graph,scheduled
from postopt import fuse,write
from canc import simplify
from smilp import solve
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/rewrite117_20260922/paired';out.mkdir(exist_ok=True)
DX,DY,pl=pickle.load(open(ROOT/'src/post151_sa/sat116/champ117.pkl','rb'));_,kg=pickle.load(open(ROOT/'src/post151_sa/runs/p6_117_16000_2.pkl','rb'))
def conv(ops):return [('cx',(o[1],o[2]),None) if o[0]=='cx' else ('u3',(o[1],),o[2]) for o in ops]
L=fuse(conv(loader_ops(full_gates(DX),XW)+loader_ops(full_gates(DY),YW)))
K=[('cx',(PHYS[g[1]],PHYS[g[2]]),None) if g[0]=='C' else ('u3',(PHYS[g[1]],),np.diag([1,np.exp(1j*g[2])])) for g in kg if g[0]!='S']
assert kg[0][1]==list(range(18))
def assemble(L):
 inv=[g if g[0]=='cx' else ('u3',g[1],g[2].conj().T) for g in reversed(L)]
 return fuse(simplify(fuse(L+K+inv),False))
base=assemble(L);ms=moves(L);pool=[];rows=[];start=time.monotonic();print('BASE',score(base),'moves',len(ms),flush=True)
for k,m in enumerate(ms):
 ll=rewrite(L,m);cand=assemble(ll);sc=score(cand)
 original=cand;g=graph(original)
 for seed in range(3):
  cc=scheduled(original,g,seed);ss=score(cc)
  if ss<sc:cand,sc=cc,ss
 row={'index':k,'move':m,'score':sc};rows.append(row)
 pool.append((sc,k,cand));pool.sort(key=lambda v:v[:2]);pool=pool[:24]
 if sc[0]<117:
  path=out/f'improved_{k}_d{sc[0]}.qasm';write(cand,path);print('IMPROVED',path,flush=True)
 if k%50==0:print(k,len(ms),'best',pool[0][:2],round(time.monotonic()-start),flush=True)
for sc,k,cand in pool:
 path=out/f'candidate_{k}_d{sc[0]}.qasm';write(cand,path);rows[k]['path']=str(path)
 exact=solve(cand,116,tlim=15,verbose=False);rows[k]['found116']=exact is not None
 if exact is not None:write(fuse(exact),out/f'exact_{k}_d116.qasm');print('EXACT SUCCESS',k,flush=True)
(out/'report.json').write_text(json.dumps({'rows':rows,'retained':[r for r in rows if 'path' in r],'seconds':time.monotonic()-start},indent=2))
print('DONE',pool[0][:2],flush=True)
