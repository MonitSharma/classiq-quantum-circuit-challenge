"""Phase comparator using parallel propagate-prefix products (two clean helpers).
Compared to ripple carry, the final phase is applied without materializing
any carry bits. This is a comparator component, not the logo oracle.
"""
import json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from post218_beam_phase import psynth
from depth_parity_network import walsh
from distributed_frame_search import native

def build(enabled):
 n=4;flag=9;h0=10 if enabled else 9;h1=h0+1;size=h1+1
 # Physical a=[0:4], v=[4:8], sign=8. Compute P=a XOR ~v.
 e=QuantumCircuit(size);e.x(list(range(4,8)));e.x(8)
 for i in range(4):e.cx(i,4+i)
 # D_c=a0 XOR (1-sign), D_i=a_(i+1) XOR a_i.
 e.cx(0,8);e.cx(1,0);e.cx(2,1);e.cx(3,2)
 # Prefixes P3*P2 and P1*P0 are disjoint, so can be computed in parallel.
 e.rccx(7,6,h0);e.rccx(5,4,h1)
 # carry = a3 XOR P3*D2 XOR t*D1 XOR t*P1*D0 XOR t*u*Dc.
 wires=[3,7,2,h0,1,5,0,h1,8]+([flag] if enabled else [])
 phases=[]
 for v in range(1<<len(wires)):
  a,p3,d2,t,d1,p1,d0,u,dc=[v>>i&1 for i in range(9)]
  on=v>>9&1 if enabled else 1
  phases.append(math.pi*on*(a+p3*d2+t*d1+t*p1*d0+t*u*dc))
 co=walsh(phases);targets={m:float(co[m]) for m in range(1,len(co)) if abs(co[m])>1e-12}
 best=None
 for seed in range(40):
  k=native(psynth(len(wires),targets,seed=seed,beam=12,branch=6,global_phase=float(co[0])))
  q=native(e.compose(k,wires).compose(e.inverse()));score=(q.depth(),q.count_ops().get('cx',0))
  if best is None or score<best[0]:best=(score,q,seed,k.depth())
 return best

def run(out):
 assert not out.exists();out.mkdir(parents=True);rows=[]
 for enabled in [False,True]:
  score,q,seed,kdepth=build(enabled);path=out/f'prefix_enabled{int(enabled)}.qasm';path.write_text(qasm2.dumps(q));q=qasm2.load(path)
  phase=None;error=0.
  for w in range(1<<(9+int(enabled))):
   r=w&15;v=w>>4&15;s=w>>8&1;flag=w>>9&1 if enabled else 1;want=(-1)**int(flag and v<=r-s)
   state=Statevector.from_int(w,1<<q.num_qubits).evolve(q).data
   if phase is None:phase=state[w]/want;phase/=abs(phase)
   state[w]-=phase*want;error=max(error,float(max(abs(state))))
  assert error<1e-10,error
  row=dict(enabled=enabled,depth=score[0],cx=score[1],width=q.num_qubits,clean_helpers=2,seed=seed,kernel_depth=kdepth,inputs_checked=1<<(9+int(enabled)),error=error);rows.append(row);print(row,flush=True)
  (out/'report.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True)
 run(p.parse_args().outdir)
