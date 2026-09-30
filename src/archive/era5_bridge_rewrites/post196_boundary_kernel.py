"""Beam phase scheduling with actual encoder arrival and inverse tail times."""
import argparse,json,math,time
from pathlib import Path
import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Operator
from build_two_stage_196 import encoders,KERNEL_WIRES
from distributed_frame_search import native
from depth_parity_network import walsh
from post218_beam_phase import psynth
from post258_joint_encoder_schedule import touches
from exhaustive_verify import exhaustive

def run(out,seeds):
 assert not out.exists();out.mkdir(parents=True)
 enc=encoders(json.loads(Path('artifacts/196/class_codes.json').read_text()),99,155)
 fulltimes=touches(enc);arrival=[fulltimes[w] for w in KERNEL_WIRES]
 co=np.array(json.loads(Path('artifacts/218/kernel_recipe.json').read_text())['co'])*math.pi/32
 targets={m:float(co[m]) for m in range(1,256) if abs(co[m])>1e-12}
 reference=Operator(qasm2.load('artifacts/196/kernel.qasm'))
 best=(196,858);rows=[];start=time.time()
 for seed in range(seeds):
  shift=min(arrival);initial=[t-shift for t in arrival]
  k=psynth(8,targets,seed=seed,beam=24,branch=8,alpha=(4,5,6)[seed%3],
           timew=(.25,.6,1.0)[seed//3%3],global_phase=float(co[0]),
           initial_times=initial,final_times=initial)
  for reverse in (False,True):
   kk=native(k.reverse_ops() if reverse else k)
   assert reference.equiv(Operator(kk))
   q=native(enc.compose(kk,KERNEL_WIRES).compose(enc.inverse()))
   text=qasm2.dumps(q);q=qasm2.loads(text);score=(q.depth(),q.count_ops().get('cx',0))
   row=dict(seed=seed,reverse=reverse,depth=score[0],cx=score[1],kernel_depth=kk.depth());rows.append(row)
   if score<best:
    f=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';f.write_text(text);exhaustive(f)
    (out/f'kernel_d{score[0]}_cx{score[1]}.qasm').write_text(qasm2.dumps(kk));best=score;row['path']=str(f)
    print('improvement',row,flush=True)
  print('seed',seed,'best',best,'last',rows[-2:],'elapsed',round(time.time()-start),flush=True)
  (out/'report.json').write_text(json.dumps(dict(best=best,arrival=arrival,rows=rows),indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=24);a=p.parse_args();run(a.outdir,a.seeds)
