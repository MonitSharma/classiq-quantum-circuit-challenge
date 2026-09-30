"""Bounded scheduling refinement for the lowest-support care-state LP kernel."""
import sys,json,math,time,argparse
from pathlib import Path
sys.path.insert(0,'src')
import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Operator
from post218_beam_phase import psynth
from distributed_frame_search import native
from build_two_stage_196 import encoders,KERNEL_WIRES
from exhaustive_verify import exhaustive
p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=160);args=p.parse_args()
out=args.outdir;assert not out.exists();out.mkdir(parents=True)
record=json.loads(Path('artifacts/post196_care_phase_lp_v1/screen.json').read_text())['candidates'][0]
co=np.array(record['co'])*math.pi;targets={i:float(co[i]) for i in range(1,256) if abs(co[i])>1e-10}
e=encoders(json.loads(Path('artifacts/196/class_codes.json').read_text()),99,155)
rows=[];best=(196,858);start=time.time()
for seed in range(args.seeds):
 config=dict(seed=seed,beam=64,branch=14,alpha=[4,5,6,7][seed%4],timew=[.15,.35,.6,.9][seed//4%4],global_phase=float(co[0]))
 k=native(psynth(8,targets,**config))
 if k.depth()<=47:
  q=native(e.compose(k,KERNEL_WIRES).compose(e.inverse()));score=(q.depth(),q.count_ops().get('cx',0));row=dict(**config,kernel_depth=k.depth(),depth=score[0],cx=score[1]);rows.append(row)
  if score<best:
   f=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';f.write_text(qasm2.dumps(q));exhaustive(f);best=score
   (out/f'kernel_d{score[0]}_cx{score[1]}.qasm').write_text(qasm2.dumps(k));(out/f'recipe_d{score[0]}_cx{score[1]}.json').write_text(json.dumps(dict(co=record['co'],config=config),indent=2));print('IMPROVEMENT',row,flush=True)
 if seed%10==0:print('tune',seed,'best',best,'elapsed',round(time.time()-start),flush=True)
 (out/'report.json').write_text(json.dumps(dict(best=best,seeds_completed=seed+1,rows=rows),indent=2))
