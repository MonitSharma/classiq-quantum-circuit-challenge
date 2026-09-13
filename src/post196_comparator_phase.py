"""Phase-only comparator: avoid computing the final carry into a qubit.
The majority carry phase is a triangle of CZs, or its enabled diagonal.
"""
import json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from post196_arithmetic_probe import comparator
from post218_beam_phase import psynth
from depth_parity_network import walsh
from distributed_frame_search import native

def run():
 out=Path('artifacts/post196_comparator_phase');assert not out.exists();out.mkdir();rows=[]
 for n,enabled in [(3,False),(4,False),(4,True)]:
  total=2*n+1+int(enabled);s=2*n;q=QuantumCircuit(total);q.x(s);q.x(list(range(n,2*n)))
  compute=QuantumCircuit(total);carry=s
  for i in range(n-1):
   compute.cx(i,n+i);compute.cx(i,carry);compute.rccx(n+i,carry,i);carry=i
  q.compose(compute,inplace=True);wires=[n-1,2*n-1,carry]
  if enabled:wires.append(2*n+1)
  phases=[]
  for v in range(1<<len(wires)):
   a,b,c=[v>>i&1 for i in range(3)];e=v>>3 if enabled else 1
   # Integer sum is phase-equivalent to majority XOR and often sparser.
   phases.append(math.pi*e*(a*b+a*c+b*c))
  co=walsh(phases);targets={m:float(co[m]) for m in range(1,len(co)) if abs(co[m])>1e-12};choices=[]
  for seed in range(24):choices.append(native(psynth(len(wires),targets,seed=seed,beam=12,branch=6,global_phase=float(co[0]))))
  kern=min(choices,key=lambda k:(k.depth(),k.size()));q.compose(kern,wires,inplace=True);q.compose(compute.inverse(),inplace=True);q.x(list(range(n,2*n)));q.x(s);q=native(q)
  path=out/f'compare{n}_enabled{int(enabled)}.qasm';path.write_text(qasm2.dumps(q));assert Operator(comparator(n,enabled)).equiv(Operator(qasm2.load(path)))
  row=dict(n=n,enabled=enabled,depth=q.depth(),cx=q.count_ops().get('cx',0),diagonal_depth=kern.depth());rows.append(row);print(row,flush=True)
 (out/'report.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':run()
