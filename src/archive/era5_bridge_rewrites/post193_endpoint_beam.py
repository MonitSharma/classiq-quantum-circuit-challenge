"""Choose completed phase beam states with free ancilla ordering included."""
import argparse,json,math,random,time
from pathlib import Path
import numpy as np
from qiskit import qasm2
from build_two_stage_196 import encoders,KERNEL_WIRES
from post196_free_ancilla_order import finish
from post218_beam_phase import psynth
from post258_joint_encoder_schedule import touches
from distributed_frame_search import native
from exhaustive_verify import exhaustive

def mapping_of(q):
 basis=[1<<i for i in range(8)]
 for inst in q.data:
  if inst.operation.name=='cx':
   a,b=[q.find_bit(w).index for w in inst.qubits];basis[b]^=basis[a]
 assert sorted(basis)==[1<<i for i in range(8)] and basis[0]==1 and basis[4]==16
 mapping=list(range(18))
 for w,b in enumerate(basis):mapping[KERNEL_WIRES[b.bit_length()-1]]=KERNEL_WIRES[w]
 assert mapping[:12]==list(range(12))
 return mapping

def run(out,seeds,trials,arrival_aware=False):
 assert not out.exists();out.mkdir(parents=True)
 recipe=json.loads(Path('artifacts/193/kernel_recipe.json').read_text());co=np.array(recipe['co'])*math.pi
 e=encoders(recipe['class_codes'],99,155);incoming=touches(e);arrival=[incoming[w] for w in KERNEL_WIRES]
 best=(193,857);rows=[];start=time.time()
 for seed in range(seeds):
  rng=random.Random(seed+193914)
  def finalize(q,basis):
   initial=touches(q,arrival);winner=None
   for sample in range(trials):
    ops,perm,times=finish(basis,initial,rng,sample)
    # The inverse encoder tail length for original wire i is incoming[i].
    score=(max(times[w]+arrival[col] for w,col in enumerate(perm)),len(ops)+q.size())
    if winner is None or score<winner[0]:winner=(score,ops)
   score,ops=winner;result=q.copy()
   for a,b in ops:result.cx(a,b)
   return score,result
  config=dict(seed=seed,beam=64,branch=14,alpha=[4.,5.,6.,7.][seed%4],timew=[.15,.35,.6,.9][seed//4%4])
  if arrival_aware:config['initial_times']=[t-min(arrival) for t in arrival]
  k=psynth(8,{m:float(co[m]) for m in range(1,256) if abs(co[m])>1e-10},global_phase=float(co[0]),finalize=finalize,**config)
  mapping=mapping_of(k);q=native(e.compose(k,KERNEL_WIRES).compose(e.inverse(),mapping));text=qasm2.dumps(q);q=qasm2.loads(text)
  score=(q.depth(),q.count_ops().get('cx',0));row=dict(**config,depth=score[0],cx=score[1],mapping=mapping);rows.append(row)
  if score<best:
   f=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';f.write_text(text);exhaustive(f);best=score;row['path']=str(f)
   (out/f'kernel_d{score[0]}_cx{score[1]}.qasm').write_text(qasm2.dumps(native(k)))
   (out/f'recipe_d{score[0]}_cx{score[1]}.json').write_text(json.dumps(dict(config=config,co=recipe['co'],mapping=mapping,trials=trials),indent=2))
   print('IMPROVEMENT',score,flush=True)
  if seed%5==0:print('seed',seed,'current',score,'best',best,'elapsed',round(time.time()-start),flush=True)
  (out/'report.json').write_text(json.dumps(dict(best=best,seeds_completed=seed+1,trials=trials,rows=rows),indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=64);p.add_argument('--trials',type=int,default=300);p.add_argument('--arrival-aware',action='store_true');a=p.parse_args();run(a.outdir,a.seeds,a.trials,a.arrival_aware)
