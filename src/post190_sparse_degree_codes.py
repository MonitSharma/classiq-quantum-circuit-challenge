"""Bounded sparsity refinement of the split-class degree-four witnesses."""
import argparse,json,time
from pathlib import Path
import z3
from two_stage_oracle import ROWCLS,COLCLS
p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seconds',type=float,default=15);a=p.parse_args();out=a.outdir;assert not out.exists();out.mkdir(parents=True)
initial=json.loads(Path('artifacts/post190_split_degree4_v1/report.json').read_text());records=[]
for saved,classes in zip(initial,[ROWCLS,COLCLS]):
 vals=[z3.BitVec(f'v{i}',3) for i in range(64)];coef=[z3.BitVec(f'a{i}',3) for i in range(64)];s=z3.Solver();s.set(timeout=int(a.seconds*1000));mask=saved['raw_mask']
 for m in range(64):
  terms=[vals[w] for w in range(64) if w&~m==0];expr=terms[0]
  for t in terms[1:]:expr=expr^t
  s.add(coef[m]==expr)
  if m.bit_count()>4:s.add(coef[m]==0)
 for i in range(64):
  for j in range(i):
   if classes[i]!=classes[j] and ((i&mask).bit_count()%2)==((j&mask).bit_count()%2):s.add(vals[i]!=vals[j])
 chosen=[]
 for w in range(64):
  if (w&mask).bit_count()%2==0 and classes[w] not in [classes[i] for i in chosen]:chosen.append(w)
  if len(chosen)==3:break
 for w,c in zip(chosen,[0,1,2]):s.add(vals[w]==c)
 weights=[(coef[m]!=0,m.bit_count()-1) for m in range(64) if m.bit_count()>=2]
 def cost(v):return sum((m.bit_count()-1) for m,c in enumerate(v) if c and m.bit_count()>=2)
 best=dict(saved);best['weighted_cost']=cost(best['anf']);rows=[];lo=0;hi=best['weighted_cost'];start=time.time()
 for step in range(5):
  bound=(lo+hi)//2;s.push();s.add(z3.PbLe(weights,bound));status=s.check();row=dict(bound=bound,status=str(status),seconds=time.time()-start)
  if status==z3.sat:
   model=s.model();codes=[model.eval(v).as_long() for v in vals];anf=[model.eval(v).as_long() for v in coef];value=cost(anf);best.update(codes=codes,anf=anf,weighted_cost=value,terms=[sum(bool(c>>b&1) for c in anf) for b in range(3)]);hi=value-1
  elif status==z3.unsat:lo=bound+1
  s.pop();rows.append(row);print(saved['side'],row,'best cost',best['weighted_cost'],flush=True)
  if status==z3.unknown or lo>hi:break
 records.append(dict(side=saved['side'],best=best,attempts=rows));(out/'report.json').write_text(json.dumps(records,indent=2))
