"""Reselect both loader schedules for the permuted 193 kernel boundary."""
import argparse,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from post224_relative_lookup import relative
from post258_two_stage_anf import decode
from post258_joint_encoder_schedule import touches
from distributed_frame_search import native
from build_two_stage_196 import KERNEL_WIRES
from exhaustive_verify import exhaustive
import two_stage_oracle as ts

def run(out,seeds,kernel_path=Path('artifacts/193/kernel.qasm'),mapping_path=None):
 assert not out.exists();out.mkdir(parents=True)
 recipe=json.loads(Path('artifacts/193/kernel_recipe.json').read_text());codes=recipe['class_codes'];mapping=recipe['uncompute_mapping'];bags=[]
 if mapping_path is not None:mapping=json.loads(mapping_path.read_text())['mapping']
 for side,cls,mask,key in [(0,ts.ROWCLS,32,'ylab'),(1,ts.COLCLS,48,'xlab')]:
  labels=decode(codes[key]);values=[labels[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)]
  table=math.pi*np.array([[v>>b&1 for v in values] for b in range(3)]);options={}
  for seed in range(seeds):
   q,_=relative(table,seed)
   if side:q.cx(5,4)
   timing=tuple(touches(q));row=dict(seed=seed,times=timing,depth=q.depth(),cx=q.count_ops().get('cx',0))
   if timing not in options or q.size()<options[timing][0].size():options[timing]=(q,row)
  vals=list(options.values());bag=[(q,r) for q,r in vals if not any(all(a<=b for a,b in zip(s['times'],r['times'])) and s['times']!=r['times'] for _,s in vals)]
  bags.append(bag);print('side',side,'distinct',len(vals),'pareto',len(bag),flush=True)
 k=qasm2.load(kernel_path);pairs=[]
 for ey,my in bags[0]:
  for ex,mx in bags[1]:
   before=list(mx['times'][:6])+list(my['times'][:6])+list(my['times'][6:])+list(mx['times'][6:]);after=before.copy()
   for w,t in zip(KERNEL_WIRES,touches(k,[before[w] for w in KERNEL_WIRES])):after[w]=t
   predicted=max(before[w]+after[mapping[w]] for w in range(18))
   pairs.append((predicted,ey.size()+ex.size(),ey,ex,my,mx))
 best=(193,855);rows=[]
 for predicted,_,ey,ex,my,mx in sorted(pairs,key=lambda p:p[:2])[:300]:
  e=QuantumCircuit(18);e.compose(ey,ts.YW+ts.YA,inplace=True);e.compose(ex,ts.XW+ts.XA,inplace=True)
  raw=e.compose(k,KERNEL_WIRES).compose(e.inverse(),mapping);assert raw.depth()==predicted
  q=native(raw);text=qasm2.dumps(q);q=qasm2.loads(text);score=(q.depth(),q.count_ops().get('cx',0));r=dict(depth=score[0],cx=score[1],predicted=predicted,y=my,x=mx);rows.append(r)
  if score<best:
   f=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';f.write_text(text);exhaustive(f);best=score;r['path']=str(f);print('improvement',r,flush=True)
 (out/'report.json').write_text(json.dumps(dict(best=best,seeds=seeds,kernel_path=str(kernel_path),mapping=mapping,pareto=[len(b) for b in bags],pairs=len(pairs),rows=rows),indent=2));print('finished',best,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=256);p.add_argument('--kernel',type=Path,default=Path('artifacts/193/kernel.qasm'));p.add_argument('--mapping',type=Path);a=p.parse_args();run(a.outdir,a.seeds,a.kernel,a.mapping)
