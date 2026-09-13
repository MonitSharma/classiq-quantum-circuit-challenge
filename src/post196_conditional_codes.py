"""Promised-domain phase expansions conditioned on previously loaded code bits.
LP is an exact-equation sparsity heuristic, not a minimum-support proof. Every
phase table is checked on all 64 reachable inputs before native construction.
"""
import argparse,itertools,json,math
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from post258_two_stage_anf import decode
from depth_parity_network import walsh
from post224_clean_parity import synth_clean
from distributed_frame_search import native
import two_stage_oracle as ts

def expansion(values,bit,previous):
 addresses=[v|sum(((int(values[v])>>b)&1)<<(6+j) for j,b in enumerate(previous)) for v in range(64)]
 n=6+len(previous);A=np.array([[(-1)**((a&m).bit_count()%2) for m in range(1<<n)] for a in addresses],float)
 target=np.array([int(v)>>bit&1 for v in values],float);weights=np.ones(1<<n);best=None
 for step in range(5):
  result=linprog(np.r_[weights,weights],A_eq=np.c_[A,-A],b_eq=target,bounds=(0,None),method='highs');assert result.success
  co=result.x[:1<<n]-result.x[1<<n:];co[abs(co)<1e-10]=0
  assert np.max(abs(A@co-target))<1e-9
  score=int(np.count_nonzero(co))
  if best is None or score<best[0]:best=(score,co.copy())
  weights=1/(abs(co)+.01)
 return best

def run(outdir,seeds):
 assert not outdir.exists();outdir.mkdir(parents=True);codes=json.loads(Path('artifacts/196/class_codes.json').read_text());records=[]
 for side,cls,mask,key in [(0,ts.ROWCLS,32,'ylab'),(1,ts.COLCLS,48,'xlab')]:
  lab=decode(codes[key]);values=[lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)]
  choices=[]
  for order in itertools.permutations(range(3)):
   pieces=[expansion(values,b,list(order[:i])) for i,b in enumerate(order)]
   row=dict(side=side,order=order,supports=[p[0] for p in pieces]);choices.append((sum(row['supports']),row,pieces));print('conditional',row,flush=True)
  for _,row,pieces in sorted(choices,key=lambda v:v[0])[:2]:
   e=QuantumCircuit(9);depths=[]
   for i,(bit,(_,coeff)) in enumerate(zip(row['order'],pieces)):
    n=6+i;co=np.zeros(1<<(n+1));co[1<<n:]=-math.pi*coeff/2;phases=walsh(co)*len(co);options=[]
    for seed in range(seeds):
     q=QuantumCircuit(9);q.h(n);q.compose(synth_clean(phases,2-i,seed),inplace=True);q.h(n);q=native(q);options.append(q)
    q=min(options,key=lambda q:(q.depth(),q.size()));depths.append(q.depth())
    wires=list(range(6))+[6+b for b in row['order'][:i]]+[6+bit]+[6+b for b in row['order'][i+1:]]
    e.compose(q,wires,inplace=True)
   e=native(e);err=0.
   for v in range(64):
    s=Statevector.from_int(v,512).evolve(e).data;w=v|(values[v]<<6);assert abs(s[w])>.99
    wanted=np.zeros(512,complex);wanted[w]=s[w]/abs(s[w]);err=max(err,float(max(abs(s-wanted))))
   assert err<1e-9;row.update(depth=e.depth(),cx=e.count_ops().get('cx',0),stage_depths=depths,error=err);records.append(row)
   (outdir/f"side{side}_order{''.join(map(str,row['order']))}.qasm").write_text(qasm2.dumps(e));print('native conditional',row,flush=True)
   (outdir/'report.json').write_text(json.dumps(records,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=4);a=p.parse_args();run(a.outdir,a.seeds)
