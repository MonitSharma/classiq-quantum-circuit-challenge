"""Find low-degree class-separating codes, allowing within-class splitting."""
import argparse,itertools,json,time
from pathlib import Path
import z3
from two_stage_oracle import ROWCLS,COLCLS

def run(out,degree,seconds):
 assert not out.exists();out.mkdir(parents=True);records=[]
 for side,classes,mask in [('y',ROWCLS,32),('x',COLCLS,48)]:
  vals=[z3.BitVec(f'{side}_{v}',3) for v in range(64)];s=z3.Solver();s.set(timeout=int(seconds*1000))
  for a in range(64):
   for b in range(a):
    if classes[a]!=classes[b] and ((a&mask).bit_count()%2)==((b&mask).bit_count()%2):s.add(vals[a]!=vals[b])
  for monomial in range(64):
   if monomial.bit_count()<=degree:continue
   subsets=[w for w in range(64) if w&~monomial==0];expr=vals[subsets[0]]
   for w in subsets[1:]:expr=expr^vals[w]
   s.add(expr==0)
  # Global affine recoding of three output bits preserves their degree.
  chosen=[]
  for w in range(64):
   if (w&mask).bit_count()%2==0 and classes[w] not in [classes[v] for v in chosen]:chosen.append(w)
   if len(chosen)==3:break
  for w,code in zip(chosen,[0,1,2]):s.add(vals[w]==code)
  start=time.time();status=s.check();record=dict(side=side,raw_mask=mask,degree=degree,status=str(status),seconds=time.time()-start)
  if status==z3.sat:
   m=s.model();codes=[m.eval(v).as_long() for v in vals];anf=codes.copy()
   for bit in range(6):
    for w in range(64):
     if w>>bit&1:anf[w]^=anf[w^(1<<bit)]
   assert max(w.bit_count() for w,a in enumerate(anf) if a)<=degree
   for a in range(64):
    for b in range(a):
     if classes[a]!=classes[b] and ((a&mask).bit_count()%2)==((b&mask).bit_count()%2):assert codes[a]!=codes[b]
   record.update(codes=codes,anf=anf,terms=[sum(bool(a>>bit&1) for a in anf) for bit in range(3)])
  elif status==z3.unknown:record['reason']=s.reason_unknown()
  records.append(record);(out/'report.json').write_text(json.dumps(records,indent=2));print({k:v for k,v in record.items() if k not in ('codes','anf')},flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--degree',type=int,default=4);p.add_argument('--seconds',type=float,default=45);a=p.parse_args();run(a.outdir,a.degree,a.seconds)
