"""Bounded shared Boolean code synthesis with free class labels.

Find three affine outputs of a shared six-input XOR/AND network that separate
classes within a retained raw parity. Labels are solver variables, not fixed
binary radius values. This is an irreversible Boolean feasibility screen;
a witness is not a quantum circuit or a native-depth claim.
"""
import argparse,json,time,itertools
from pathlib import Path
import z3
from multioutput_minmc import FULL,INPUTS,affine,eval_xag
from two_stage_oracle import ROWCLS,COLCLS

def solve(side,count,seconds,class_table=None,raw_mask=None):
 cls,raw=(ROWCLS,32) if side=='y' else (COLCLS,48)
 if class_table is not None:cls=class_table
 if raw_mask is not None:raw=raw_mask
 groups={}
 for v in range(64):groups.setdefault(((v&raw).bit_count()%2,int(cls[v])),[]).append(v)
 s=z3.Solver();s.set(timeout=int(seconds*1000));signals=[z3.BitVecVal(v,64) for v in [FULL,*INPUTS]];spec=[]
 for n in range(count):
  a=[z3.Bool(f'a_{n}_{i}') for i in range(len(signals))];b=[z3.Bool(f'b_{n}_{i}') for i in range(len(signals))]
  z=z3.BitVec(f'node_{n}',64);s.add(z==affine(a,signals)&affine(b,signals));signals.append(z);spec.append((a,b))
 outs=[[z3.Bool(f'o_{j}_{i}') for i in range(len(signals))] for j in range(3)]
 truth=[affine(a,signals) for a in outs];labels={key:z3.BitVec(f'code_{key[0]}_{key[1]}',3) for key in groups}
 for key,vs in groups.items():
  for v in vs:
   for j in range(3):s.add(z3.Extract(v,v,truth[j])==z3.Extract(j,j,labels[key]))
 for rawbit in (0,1):s.add(z3.Distinct([value for key,value in labels.items() if key[0]==rawbit]))
 # Any three distinct vectors over GF(2) can be affinely mapped to 0,1,2.
 keys=sorted(key for key in groups if key[0]==0)
 for key,value in zip(keys,(0,1,2)):s.add(labels[key]==value)
 start=time.time();status=s.check();row=dict(side=side,and_bound=count,status=str(status),seconds=time.time()-start)
 if status==z3.unknown:row['reason']=s.reason_unknown()
 if status==z3.sat:
  m=s.model()
  def indices(cs):return [i for i,c in enumerate(cs) if z3.is_true(m.eval(c,model_completion=True))]
  xag=dict(and_count=count,and_nodes=[dict(left=indices(a),right=indices(b)) for a,b in spec],outputs=[indices(a) for a in outs])
  ts=eval_xag(xag);codes=[sum(((t>>v)&1)<<j for j,t in enumerate(ts)) for v in range(64)]
  for key,vs in groups.items():assert len({codes[v] for v in vs})==1
  for a,b in itertools.combinations(range(64),2):
   if ((a&raw).bit_count()%2)==((b&raw).bit_count()%2) and cls[a]!=cls[b]:assert codes[a]!=codes[b]
  row.update(xag=xag,codes=codes,truth_tables=ts,checked_inputs=64)
 return row

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seconds',type=float,default=8);a=p.parse_args();assert not a.outdir.exists();a.outdir.mkdir(parents=True);rows=[]
 for count in (4,5,6):
  for side in ('x','y'):
   r=solve(side,count,a.seconds);rows.append(r);print(r,flush=True);(a.outdir/'report.json').write_text(json.dumps(rows,indent=2))
