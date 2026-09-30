"""Native benchmark of a sign-adjusted four-bit magnitude comparator.
No full-oracle claim: mode decoding, radius loading, and rectangles are separate.
"""
import json,itertools
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from distributed_frame_search import native

def comparator(n,enabled=False):
 # a: radius, b: one's-complement folded magnitude, s: original sign.
 # Carry out of r + ~v + (1-s) means v <= r-s.
 count=2*n+1+int(enabled);q=QuantumCircuit(count);s=2*n
 q.x(s);q.x(list(range(n,2*n)))
 compute=QuantumCircuit(count);carry=s
 for i in range(n):
  a,b=i,n+i
  compute.cx(a,b);compute.cx(a,carry);compute.rccx(b,carry,a);carry=a
 q.compose(compute,inplace=True)
 if enabled:q.cz(n-1,2*n+1)
 else:q.z(n-1)
 q.compose(compute.inverse(),inplace=True);q.x(list(range(n,2*n)));q.x(s)
 return native(q)

def run():
 out=Path('artifacts/post196_arithmetic_probe');assert not out.exists();out.mkdir();rows=[]
 for n,enabled in [(3,False),(4,False),(4,True)]:
  q=comparator(n,enabled);path=out/f'compare_{n}_enabled{int(enabled)}.qasm';path.write_text(qasm2.dumps(q))
  op=Operator(qasm2.load(path)).data;want=np.ones(1<<q.num_qubits)
  for w in range(len(want)):
   r=w&((1<<n)-1);v=(w>>n)&((1<<n)-1);s=(w>>(2*n))&1;e=(w>>(2*n+1))&1 if enabled else 1
   want[w]=(-1)**int(e and v<=r-s)
  target=np.diag(want);phase=np.vdot(target,op);err=float(np.max(abs(op-phase/abs(phase)*target)));assert err<1e-10,err
  row=dict(n=n,enabled=enabled,depth=q.depth(),cx=q.count_ops().get('cx',0),width=q.num_qubits,error=err);rows.append(row);print(row,flush=True)
 # Reversible x preprocessing: y5-controlled reflection, subtract eight mod32,
 # then one's-complement fold of the low four bits around the shared center.
 q=QuantumCircuit(7)
 for i in range(5):q.cx(6,i)
 q.x(3);q.cx(3,4)
 for i in range(4):q.cx(4,i)
 q=native(q);path=out/'fold.qasm';path.write_text(qasm2.dumps(q));op=Operator(qasm2.load(path)).data
 for w in range(128):
  x=w&63;y5=w>>6
  transformed=x^(31 if y5 else 0);d=((transformed&31)-8)%32;sign=d>>4;fold=(d&15)^(15 if sign else 0)
  expected=fold|(sign<<4)|(x&32)|(y5<<6)
  assert abs(op[expected,w])>1-1e-10
 row=dict(component='reflection_and_fold',depth=q.depth(),cx=q.count_ops().get('cx',0),width=q.num_qubits);rows.append(row);print(row,flush=True)
 (out/'report.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':run()
