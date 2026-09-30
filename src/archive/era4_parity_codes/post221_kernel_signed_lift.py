"""Optimize odd integer weights of kernel ANF monomials modulo full turns."""
import json,math,random,argparse
from pathlib import Path
import numpy as np
from qiskit import qasm2,QuantumCircuit
from qiskit.quantum_info import Operator
from depth_parity_network import walsh
from post258_kernel_schedule import synth
from distributed_frame_search import native

def run(outdir,steps,seeds):
 assert not outdir.exists();outdir.mkdir(parents=True);r=json.loads(Path('artifacts/221/class_codes.json').read_text());terms=r['terms'];rng=np.random.default_rng(831)
 cubes=np.array([[int(m&~w==0) for w in range(256)] for m in terms]);sp=np.array([walsh(t)*32 for t in cubes]);assert np.max(abs(sp-sp.round()))<1e-9;sp=sp.round().astype(int)
 # Rz angle is -2*pi*co; integer shifts of co are only global phases.
 coeff=np.ones(len(terms),int);cur=coeff@sp;cur[0]=0;cur%=32
 incidence=np.array([[m>>b&1 for b in range(8)] for m in range(256)])
 def scores(a):
  nz=a!=0
  return nz.sum(axis=-1)+.12*(nz@incidence).max(axis=-1)
 best=float(scores(cur));candidates=[];seen=set()
 for step in range(steps):
  if step%1000==0:coeff=rng.choice([-3,-1,1,3],len(terms));cur=coeff@sp;cur[0]=0;cur%=32
  moves=(cur[None,:]+2*sp)%32;moves[:,0]=0;vals=scores(moves);idx=int(rng.choice(np.flatnonzero(vals==vals.min())));cost=float(vals[idx]);temp=.1+2*(1-(step%1000)/1000)
  if cost<=scores(cur) or rng.random()<math.exp(min(0,(scores(cur)-cost)/temp)):coeff[idx]+=2;cur=moves[idx]
  else:
   idx=int(rng.integers(len(terms)));cost=float(vals[idx])
   if rng.random()<math.exp(min(0,(scores(cur)-cost)/temp)):coeff[idx]+=2;cur=moves[idx]
  cost=float(scores(cur));key=tuple(cur)
  if cost<=best+2 and key not in seen:
   seen.add(key);phases=math.pi*(coeff@cubes);row=dict(step=step,support=int(np.count_nonzero(cur)),cost=cost,coefficients=coeff.tolist());candidates.append((cost,phases,row))
  if cost<best:best=cost;print('best phase',step,best,np.count_nonzero(cur),flush=True)
 candidates.sort(key=lambda t:t[0]);bestnative=(9999,9999);rows=[]
 for _,phases,row in candidates[:20]:
  for seed in range(seeds):
   # Use the reduced, equivalent phase representation to expose full-turn deletions.
   co=walsh(phases/math.pi);co=(co+.5)%1-.5;co[0]=0;reduced=walsh(co)*256*math.pi
   k=native(synth(reduced,seed));score=(k.depth(),k.count_ops().get('cx',0))
   if score<bestnative:
    bestnative=score;path=outdir/f'kernel_d{score[0]}_cx{score[1]}.qasm';path.write_text(qasm2.dumps(k));op=Operator(qasm2.load(path)).data;want=np.diag(np.exp(1j*phases));overlap=np.vdot(want,op);err=float(np.max(abs(op-overlap/abs(overlap)*want)));assert err<1e-10
    result=dict(**row,seed=seed,depth=score[0],cx=score[1],path=str(path),error=err);rows.append(result);print('native',result,flush=True)
 (outdir/'report.json').write_text(json.dumps(dict(rows=rows,steps=steps,seeds=seeds,candidates=len(candidates)),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--steps',type=int,default=20000);p.add_argument('--seeds',type=int,default=20);a=p.parse_args();run(a.outdir,a.steps,a.seeds)
