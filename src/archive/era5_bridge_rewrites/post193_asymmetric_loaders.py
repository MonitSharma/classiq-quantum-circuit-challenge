"""Choose different compute/uncompute schedules with identical input phase."""
import argparse,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from post224_relative_lookup import relative
from distributed_ucry import structured_ucry
from post258_two_stage_anf import decode
from post258_joint_encoder_schedule import touches
from build_two_stage_196 import KERNEL_WIRES
from distributed_frame_search import native
from exhaustive_verify import exhaustive
import two_stage_oracle as ts

def gauge(table,values,seed):
 raw=structured_ucry(table,[6,7,8],list(range(6)),seed,sparse=False,open_walk=True)
 body=list(raw.data)[3:-3]
 while body and body[-1].operation.name=='cx':
  a,b=[raw.find_bit(w).index for w in body[-1].qubits]
  if a>=6 or b<6:break
  body.pop()
 v=np.arange(64,dtype=int);phase=np.zeros(64,dtype=int)
 for inst in body:
  ws=[raw.find_bit(w).index for w in inst.qubits]
  if inst.operation.name=='cx':v^=((v>>ws[0]&1)<<ws[1])
  else:
   assert inst.operation.name=='rz'
   unit=float(inst.operation.params[0])*64/math.pi;assert abs(unit-round(unit))<1e-9
   phase+=round(unit)*(2*(v>>ws[0]&1)-1)
 assert np.array_equal(v&63,np.arange(64))
 phase+=128*np.array([((int(w)>>6)&int(c)).bit_count()%2 for w,c in zip(v,values)])
 return tuple(((phase-phase[0])%256).tolist())

def run(out,seeds,limit=120):
 assert not out.exists();out.mkdir(parents=True)
 recipe=json.loads(Path('artifacts/193/kernel_recipe.json').read_text());bags=[]
 for side,cls,mask,key in [(0,ts.ROWCLS,32,'ylab'),(1,ts.COLCLS,48,'xlab')]:
  lab=decode(recipe['class_codes'][key]);values=[lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)]
  tab=math.pi*np.array([[v>>b&1 for v in values] for b in range(3)]);options={}
  for seed in range(seeds):
   phase=gauge(tab,values,seed);e,_=relative(tab,seed)
   if side:e.cx(5,4)
   timing=tuple(touches(e));key=(phase,timing)
   row=dict(seed=seed,times=timing,phase=phase)
   if key not in options or e.size()<options[key][0].size():options[key]=(e,row)
  vals=list(options.values());bags.append(vals);print('side',side,'options',len(vals),'phase groups',len({m['phase'] for _,m in vals}),flush=True)
 k=qasm2.load('artifacts/post193_endpoint_beam_v1/kernel_d193_cx855.qasm');mapping=json.loads(Path('artifacts/post193_endpoint_beam_v1/recipe_d193_cx855.json').read_text())['mapping']
 encs=[]
 for ey,my in bags[0]:
  for ex,mx in bags[1]:
   times=tuple(mx['times'][:6]+my['times'][:6]+my['times'][6:]+mx['times'][6:]);encs.append((times,ey,ex,my,mx))
 byphase={}
 for item in encs:byphase.setdefault((item[3]['phase'],item[4]['phase']),[]).append(item)
 candidates=[]
 for before,ey,ex,my,mx in encs:
  after=list(before)
  for w,t in zip(KERNEL_WIRES,touches(k,[before[w] for w in KERNEL_WIRES])):after[w]=t
  for tail,fy,fx,ny,nx in byphase[(my['phase'],mx['phase'])]:
   depth=max(tail[w]+after[mapping[w]] for w in range(18));size=ey.size()+ex.size()+fy.size()+fx.size()
   candidates.append((depth,size,ey,ex,fy,fx,my['seed'],mx['seed'],ny['seed'],nx['seed']))
 print('asymmetric pairs',len(candidates),'best predicted',min(c[0] for c in candidates),flush=True)
 best=(193,854);rows=[]
 ordered=sorted(candidates,key=lambda c:c[:2]);depths=sorted({c[0] for c in ordered})[:3]
 selected=[]
 for depth in depths:selected.extend([c for c in ordered if c[0]==depth][:max(1,limit//len(depths))])
 for predicted,_,ey,ex,fy,fx,ys,xs,yt,xt in selected:
  e=QuantumCircuit(18);f=QuantumCircuit(18)
  for q,y,x in ((e,ey,ex),(f,fy,fx)):q.compose(y,ts.YW+ts.YA,inplace=True);q.compose(x,ts.XW+ts.XA,inplace=True)
  raw=e.compose(k,KERNEL_WIRES).compose(f.inverse(),mapping);assert raw.depth()==predicted
  q=native(raw);text=qasm2.dumps(q);q=qasm2.loads(text);score=(q.depth(),q.count_ops().get('cx',0));row=dict(depth=score[0],cx=score[1],forward=[ys,xs],inverse=[yt,xt]);rows.append(row)
  if score<best:
   p=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';p.write_text(text);exhaustive(p);row['path']=str(p);best=score;print('IMPROVEMENT',row,flush=True)
 (out/'report.json').write_text(json.dumps(dict(best=best,seeds=seeds,pairs=len(candidates),limit=limit,rows=rows),indent=2));print('finished',best,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=160);p.add_argument('--limit',type=int,default=120);a=p.parse_args();run(a.outdir,a.seeds,a.limit)
