"""Reweighted LP over the kernel's unreachable-state phase freedom.

Keep real phases exact on reachable states for each selected integer lift.
No claim of globally minimal support or depth is made by the LP heuristic.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from qiskit import qasm2
from qiskit.quantum_info import Operator
from build_two_stage_196 import encoders,KERNEL_WIRES
from distributed_frame_search import native
from post258_two_stage_anf import decode
from post218_beam_phase import psynth
from exhaustive_verify import exhaustive

def run(out,restarts):
 assert not out.exists();out.mkdir(parents=True)
 codes=json.loads(Path('artifacts/196/class_codes.json').read_text())
 y,x=decode(codes['ylab']),decode(codes['xlab'])
 care=np.array(sorted({a[0]|b<<1|(c[0]|d<<1)<<4 for a,b in y.items() for c,d in x.items()}))
 H=np.array([[(-1)**((int(w)&m).bit_count()%2) for m in range(256)] for w in care],float)
 original=np.array(json.loads(Path('artifacts/218/kernel_recipe.json').read_text())['co'],float)/32
 targets=[H@original,np.array([sum(m&~int(w)==0 for m in codes['terms'])%2 for w in care],float)]
 rng=np.random.default_rng(914);matrix=np.c_[H,-H];pool={};screen=[]
 for restart in range(restarts):
  lift=restart%2;target=targets[lift];weights=np.exp(rng.normal(0,.8,256));co=original.copy()
  for step in range(8):
   weights[0]=0
   sol=linprog(np.r_[weights,weights],A_eq=matrix,b_eq=target,bounds=(0,None),method='highs')
   assert sol.success,sol.message
   co=sol.x[:256]-sol.x[256:];co[abs(co)<1e-9]=0
   error=float(np.max(abs(H@co-target)));assert error<1e-8,error
   count=int(np.count_nonzero(co[1:]));key=tuple(np.round(co,10))
   pool[key]=dict(co=co.tolist(),support=count,lift=lift,restart=restart,error=error)
   weights=1/(abs(co)+.03)*np.exp(rng.normal(0,.2,256))
  screen.append(dict(restart=restart,lift=lift,support=count))
  if restart%8==0:print('LP',restart,'best support',min(r['support'] for r in pool.values()),flush=True)
 candidates=sorted(pool.values(),key=lambda r:r['support'])[:10]
 (out/'screen.json').write_text(json.dumps(dict(restarts=restarts,screen=screen,candidates=candidates),indent=2))
 enc=encoders(codes,99,155);best=(196,858);records=[]
 for idx,row in enumerate(candidates):
  if row['support']>85:continue
  co=np.array(row['co'])*math.pi;wanted=np.exp(1j*(H@co))
  for seed in (209,14,19,47,83,113):
   k=native(psynth(8,{m:float(co[m]) for m in range(1,256) if abs(co[m])>1e-10},seed=seed,beam=64,branch=14,alpha=5,timew=.35,global_phase=float(co[0])))
   op=Operator(k).data[:,care];want=np.zeros_like(op);want[care,np.arange(len(care))]=wanted
   phase=np.vdot(want,op);err=float(np.max(abs(op-phase/abs(phase)*want)));assert err<1e-8,err
   q=native(enc.compose(k,KERNEL_WIRES).compose(enc.inverse()));text=qasm2.dumps(q);q=qasm2.loads(text);score=(q.depth(),q.count_ops().get('cx',0))
   record=dict(candidate=idx,seed=seed,support=row['support'],depth=score[0],cx=score[1],kernel_depth=k.depth());records.append(record)
   if score<best:
    f=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';f.write_text(text);exhaustive(f);best=score
    (out/f'kernel_d{score[0]}_cx{score[1]}.qasm').write_text(qasm2.dumps(k));record['path']=str(f)
    print('improvement',record,flush=True)
  print('compiled',idx,'support',row['support'],'best',best,flush=True)
  (out/'report.json').write_text(json.dumps(dict(best=best,rows=records),indent=2))
 print('finished',best,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--restarts',type=int,default=48);a=p.parse_args();run(a.outdir,a.restarts)
