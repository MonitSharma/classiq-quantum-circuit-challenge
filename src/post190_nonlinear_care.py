"""RCCX-conjugated reachable-state phase synthesis; bounded heuristic search.

A relative-phase permutation C surrounds a diagonal D with C.inverse().
Input-dependent RCCX phases therefore cancel. LP constrains D only on the
transformed reachable code words. Each compiled kernel is checked on every
reachable input, including leakage, before composing the complete oracle.
"""
import argparse,itertools,json,math,time
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from build_two_stage_196 import encoders,KERNEL_WIRES
from distributed_frame_search import native
from post258_two_stage_anf import decode
from post218_beam_phase import psynth
from exhaustive_verify import exhaustive


def care_truth(codes):
 y,x=decode(codes['ylab']),decode(codes['xlab'])
 care=np.array(sorted({a[0]|b<<1|(c[0]|d<<1)<<4 for a,b in y.items() for c,d in x.items()}))
 truth=np.array([sum(m&~int(w)==0 for m in codes['terms'])%2 for w in care],float)
 return care,truth


def conjugator(move):
 q=QuantumCircuit(8)
 if move is None:return q
 a,b,t,oa,ob=move
 if oa:q.x(a)
 if ob:q.x(b)
 q.rccx(a,b,t)
 if ob:q.x(b)
 if oa:q.x(a)
 return q


def permute(words,move):
 if move is None:return words.copy()
 a,b,t,oa,ob=move
 return words^(((((words>>a)&1)^oa)&(((words>>b)&1)^ob))<<t)


def solve_phase(H,truth,rng,steps,initial=None):
 matrix=np.c_[H,-H]
 weights=np.exp(rng.normal(0,.45,256)) if initial is None else 1/(abs(initial)+.03)
 best=None
 for _ in range(steps):
  weights[0]=0
  sol=linprog(np.r_[weights,weights],A_eq=matrix,b_eq=truth,bounds=(0,None),method='highs')
  assert sol.success,sol.message
  co=sol.x[:256]-sol.x[256:];co[abs(co)<1e-9]=0
  error=float(np.max(abs(H@co-truth)));assert error<1e-8,error
  score=int(np.count_nonzero(co[1:]))
  if best is None or score<best[0]:best=(score,co.copy())
  weights=1/(abs(co)+.03)*np.exp(rng.normal(0,.15,256))
 return best


def run(out,compile_count):
 assert not out.exists();out.mkdir(parents=True)
 codes=json.loads(Path('artifacts/190/class_codes.json').read_text())
 care,truth=care_truth(codes)
 had=np.array([[1-2*((w&m).bit_count()%2) for m in range(256)] for w in range(256)],float)
 moves=[None]+[(a,b,t,oa,ob) for a,b in itertools.combinations(range(8),2) for t in range(8) if t not in (a,b) for oa,ob in itertools.product((0,1),repeat=2)]
 rng=np.random.default_rng(914190);rows=[];start=time.time()
 for index,move in enumerate(moves):
  support,co=solve_phase(had[permute(care,move)],truth,rng,2)
  rows.append(dict(move=move,support=support,co=co.tolist()))
  if index%40==0:print('screen',index,'best',min(r['support'] for r in rows),'seconds',round(time.time()-start),flush=True)
 (out/'screen.json').write_text(json.dumps(rows,indent=2))
 for row in sorted(rows,key=lambda r:r['support'])[:32]:
  support,co=solve_phase(had[permute(care,row['move'])],truth,rng,6,np.array(row['co']))
  if support<row['support']:row.update(support=support,co=co.tolist())
 (out/'refined.json').write_text(json.dumps(sorted(rows,key=lambda r:r['support'])[:32],indent=2))
 enc=encoders(codes,298,506);best=(190,857);compiled=[]
 for idx,row in enumerate(sorted(rows,key=lambda r:r['support'])[:compile_count]):
  c=conjugator(row['move']);co=np.array(row['co'])*math.pi
  for seed in (56,123):
   k=psynth(8,{m:float(co[m]) for m in range(1,256) if abs(co[m])>1e-9},global_phase=float(co[0]),seed=seed,beam=96,branch=22,alpha=6.,timew=1.4,horizon=1.5,fill=2)
   kernel=native(c.compose(k).compose(c.inverse()))
   op=Operator(kernel).data[:,care];want=np.zeros_like(op);want[care,np.arange(len(care))]=np.exp(1j*math.pi*truth)
   phase=np.vdot(want,op);phase/=abs(phase);error=float(np.max(abs(op-phase*want)));assert error<1e-8,error
   q=native(enc.compose(kernel,KERNEL_WIRES).compose(enc.inverse()));source=qasm2.dumps(q);q=qasm2.loads(source)
   score=(q.depth(),q.count_ops().get('cx',0));rec=dict(move=row['move'],support=row['support'],seed=seed,depth=score[0],cx=score[1],kernel_depth=kernel.depth(),care_error=error);compiled.append(rec)
   if score<best:
    path=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';path.write_text(source);exhaustive(path);best=score
    (out/f'kernel_d{score[0]}_cx{score[1]}.qasm').write_text(qasm2.dumps(kernel));rec['path']=str(path)
   print('compiled',idx,rec,'best',best,flush=True)
   (out/'report.json').write_text(json.dumps(dict(best=best,care=len(care),screened=len(rows),compiled=compiled),indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--compile',type=int,default=8);a=p.parse_args();run(a.outdir,a.compile)
