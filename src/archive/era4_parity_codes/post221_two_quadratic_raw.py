"""Two sequential reversible quadratic coordinate tags for a 2+2 code split."""
import json,itertools,argparse
from pathlib import Path
from post224_nonlinear_tags import PAR,FULL
import two_stage_oracle as ts

def run(side):
 out=Path(f'artifacts/post221_two_quadratic_{side}_v1');assert not out.exists();out.mkdir();cls=ts.ROWCLS if side=='y' else ts.COLCLS;firsts=json.loads(Path(f'artifacts/post224_nonlinear_tags_{side}_v1/report.json').read_text())['viable'];seconds={}
 for target in range(6):
  forms=[m for m in range(1,64) if not m>>target&1];planes=sorted({tuple(sorted((a,b,a^b))) for a in forms for b in forms if a<b});bag=[]
  for plane in planes:
   a,b=plane[:2]
   for linear in [0]+forms:bag.append((PAR[1<<target]^PAR[linear]^(PAR[a]&PAR[b]),dict(target=target,a=a,b=b,linear=linear)))
  seconds[target]=bag
 best=99;rows=[];tested=0
 for first in firsts:
  t=first['target'];tag=int(first['tag']);mapping=[v^((((tag>>v)&1)^(v>>t&1))<<t) for v in range(64)];assert len(set(mapping))==64
  cm=[0]*11
  for v,w in enumerate(mapping):cm[cls[v]]|=1<<w
  first0=FULL^PAR[1<<t];first1=PAR[1<<t]
  for u,bag in seconds.items():
   if u==t:continue
   for tag2,second in bag:
    tested+=1;groups=[first0&(FULL^tag2),first1&(FULL^tag2),first0&tag2,first1&tag2];counts=[]
    for g in groups:
     count=sum(bool(m&g) for m in cm);counts.append(count)
     if count>4:break
    if len(counts)<4 or max(counts)>4:continue
    proxy=sum((r[k].bit_count() for r in [first,second] for k in ['a','b','linear']))
    row=dict(first=first,second=second,counts=counts,proxy=proxy);rows.append(row)
    if proxy<best:best=proxy;print('witness',side,row,flush=True)
 rows.sort(key=lambda r:r['proxy']);(out/'report.json').write_text(json.dumps(dict(tested=tested,witness_count=len(rows),rows=rows[:100]),indent=2)+'\n');print(side,'tested',tested,'witnesses',len(rows),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--side',choices=['y','x'],required=True);run(p.parse_args().side)
