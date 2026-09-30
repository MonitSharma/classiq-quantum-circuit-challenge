"""Conjugate coordinate classes by one cheap reversible nonlinear gate.
A two-frame code may acquire linear periods after a nonlinear change of input;
this is not covered by the previous linear-period exclusions on raw inputs.
Only physical coordinate period triples are screened here (a bounded family).
"""
import argparse,itertools,json,time
from pathlib import Path
from post218_two_frame_codes import feasible,conflict_pairs
import two_stage_oracle as ts

def run(outdir,side):
 assert not outdir.exists();outdir.mkdir(parents=True)
 cls=ts.ROWCLS if side=='y' else ts.COLCLS;rows=[];count=0;start=time.time()
 triples=list(itertools.combinations([1<<i for i in range(6)],3))
 for target in range(6):
  for a,b in itertools.combinations([i for i in range(6) if i!=target],2):
   for polarity in range(4):
    perm=[v^(((((v>>a)&1)^(polarity&1))&(((v>>b)&1)^(polarity>>1)))<<target) for v in range(64)]
    assert [perm[v] for v in perm]==list(range(64))
    transformed=[cls[v] for v in perm]
    rhos=[r for r in range(1,64) if all(len({transformed[v] for v in range(64) if (v&r).bit_count()%2==h})<=8 for h in [0,1])]
    for rho in rhos:
     pairs=conflict_pairs(transformed,rho)
     for directions in triples:
      codes=feasible(transformed,rho,directions,pairs);count+=1
      if isinstance(codes,list):
       row=dict(side=side,controls=[a,b],target=target,polarity=polarity,rho=rho,directions=directions,codes=codes,permutation=perm)
       rows.append(row);print('WITNESS',side,'gate',a,b,target,polarity,'rho',rho,'directions',directions,flush=True)
       (outdir/'witnesses.json').write_text(json.dumps(rows,indent=2))
    (outdir/'progress.json').write_text(json.dumps(dict(side=side,tested=count,witnesses=len(rows),last_gate=[a,b,target,polarity],seconds=time.time()-start),indent=2))
  print('target done',side,target,count,'witnesses',len(rows),flush=True)
 (outdir/'report.json').write_text(json.dumps(dict(side=side,tested=count,witnesses=rows,seconds=time.time()-start),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--side',choices=['x','y'],required=True);a=p.parse_args();run(a.outdir,a.side)
