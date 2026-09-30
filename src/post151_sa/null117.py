"""Redistribute a reachable-code null phase over existing parity slots."""
import os,sys,pickle,itertools,json,math
from pathlib import Path
import numpy as np
from postopt import parse_ops,fuse,write,depth
from canc import simplify
from kdrv import CO,assemble
from smilp import solve
from kgenco import build_F,CH
ROOT=Path(os.environ['CLASSIQ_ROOT']); out=ROOT/'artifacts/rewrite117_20260922/null';out.mkdir(exist_ok=True)
DX,DY,pl=pickle.load(open(ROOT/'src/post151_sa/sat116/champ117.pkl','rb'))
_,kg=pickle.load(open(ROOT/'src/post151_sa/runs/p6_117_16000_2.pkl','rb'))
rows=dict(zip(pl[1],pl[2]));slots={};rterms={}
for w,m in rows.items():slots.setdefault(m,[]).append((-1,w))
for i,g in enumerate(kg):
 if g[0]=='C': rows[g[2]]^=rows[g[1]];slots.setdefault(rows[g[2]],[]).append((i,g[2]))
 if g[0]=='R': rterms[i]=rows[g[1]]
v={0:1,1:-1,4:-1,5:1,10:-1,11:1,14:1,15:-1}
F,known=build_F();assert np.max(abs(sum(CH[m]*x for m,x in v.items())[known]))==0
records=[]
for alpha in [.125,-.0625,.0625]:
 co=CO.copy()
 for m,x in v.items():co[m]+=math.pi*alpha*x
 added=[m for m in v if m and abs(CO[m])<1e-10 and abs(co[m])>1e-10]
 for n,choices in enumerate(itertools.product(*(slots[m] for m in added))):
  additions={}
  for m,(i,w) in zip(added,choices): additions.setdefault(i,[]).append(('R',w,2*co[m]))
  body=kg[:1]+additions.get(-1,[])
  for i,g in enumerate(kg[1:],1):
   if g[0]=='R':
    m=rterms[i]
    if abs(co[m])>1e-10:body.append(('R',g[1],2*co[m]))
   else:body.append(g)
   body.extend(additions.get(i,[]))
  name=f'a{alpha}_{n}';path=out/(name+'.qasm');d,cx=assemble(DX,DY,body,path)
  ops=fuse(simplify(fuse(parse_ops(path)),False));write(ops,path)
  r={'alpha':alpha,'slots':choices,'path':str(path),'depth':depth(ops),'cx':sum(g[0]=='cx' for g in ops)}
  exact=solve(ops,116,tlim=20,verbose=False);r['found116']=exact is not None
  if exact is not None:
   p=out/(name+'_116.qasm');write(fuse(exact),p);r['improved']=str(p)
  records.append(r);print(r,flush=True)
(out/'report.json').write_text(json.dumps(records,indent=2))
