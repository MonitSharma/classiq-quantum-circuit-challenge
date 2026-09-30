import sys,json,time
sys.path.insert(0,'src')
import z3,two_stage_oracle as t
out=[]
for side,cls,raw in [('y',t.ROWCLS,5),('x',t.COLCLS,4)]:
 c=[z3.BitVec(f'{side}_{i}',3) for i in range(64)];s=z3.Solver();s.set(timeout=2000)
 for a in range(64):
  for b in range(a):
   if ((a^b)>>raw&1)==0 and cls[a]!=cls[b]:s.add(c[a]!=c[b])
 s.add(c[0]==0);res=[]
 for d in range(1,64):
  s.push();s.add([z3.Extract(0,0,c[a])==z3.Extract(0,0,c[a^d]) for a in range(64) if a<(a^d)])
  st=s.check();r=dict(direction=d,status=str(st))
  if st==z3.sat:r['labels']=[s.model().eval(v).as_long() for v in c]
  res.append(r);s.pop()
 print(side,'sat',[r['direction'] for r in res if r['status']=='sat'],'unknown',[r['direction'] for r in res if r['status']=='unknown'],flush=True)
 out.append(dict(side=side,raw=raw,results=res))
from pathlib import Path
p=Path('artifacts/post258_single_period.json')
assert not p.exists(), 'Use a new output path for another run'
p.write_text(json.dumps(out,indent=2)+'\n')
