"""No-temp lowering for XAG witnesses with independent affine output rows.

Each AND uses a clean node wire; affine controls are synthesized in place
and restored. Relative phases are allowed only within C/diagonal/C.inverse().
This does not solve pebbling when the AND count exceeds available clean wires.
"""
import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.synthesis.linear import synth_cnot_count_full_pmh
from distributed_frame_search import native
from xag import linear_best


def rank(rows):
 piv={}
 for row in rows:
  while row:
   j=row.bit_length()-1
   if j in piv:row^=piv[j]
   else:piv[j]=row;break
 return len(piv)


def lower(w):
 k=w['k'];m=len(w['outs']);n=6+k
 if not 0<m<=k:raise ValueError('this lowering needs at least one node per output')
 q=QuantumCircuit(n);wire={i:i for i in range(n)}
 def append_pre(pre):
  for inst in pre.data:q.append(inst.operation,[pre.find_bit(v).index for v in inst.qubits])
 for j,g in enumerate(w['gates']):
  forms=[]
  for key in ('a','b'):
   selected,const=g[key];assert all(i<6+j for i in selected)
   forms.append(frozenset(selected)^({-1} if const else set()))
  pre,a,b=linear_best(None,*forms,wire)
  append_pre(pre);q.rccx(a,b,6+j);append_pre(pre.inverse())
 rows=[1<<i for i in range(6)]
 for selected,const in w['outs']:rows.append(sum(1<<i for i in selected))
 if rank(rows)!=len(rows):raise ValueError('outputs not independent modulo original inputs')
 for i in range(6,n):
  if rank(rows+[1<<i])>len(rows):rows.append(1<<i)
 assert len(rows)==n
 matrix=np.array([[(r>>i)&1 for i in range(n)] for r in rows],dtype=bool)
 q.compose(synth_cnot_count_full_pmh(matrix),inplace=True)
 for j,(_,const) in enumerate(w['outs']):
  if const:q.x(6+j)
 return native(q)


def outputs(w,x):
 v=[(x>>i)&1 for i in range(6)]
 def affine(form):return int(form[1])^(sum(v[i] for i in form[0])%2)
 for g in w['gates']:v.append(affine(g['a'])&affine(g['b']))
 return [affine(form) for form in w['outs']]


def check(w):
 c=lower(w);n=c.num_qubits;m=len(w['outs']);full=c.copy()
 for j in range(m):full.z(6+j)
 full.compose(c.inverse(),inplace=True);full=native(full);error=0.;shared=None
 for x in range(64):
  s=Statevector.from_int(x,1<<n);v=s.evolve(c).data
  support=np.flatnonzero(abs(v)>1e-10);assert len(support)==1
  out=int(support[0]);assert out&63==x
  assert [(out>>(6+j))&1 for j in range(m)]==outputs(w,x)
  v=s.evolve(full).data;expected=(-1)**sum(outputs(w,x))
  if shared is None:shared=v[x]/expected
  want=np.zeros(1<<n,complex);want[x]=shared*expected
  error=max(error,float(np.max(abs(v-want))))
 assert error<1e-10
 return dict(and_count=w['k'],outputs=m,width=n,encoder_depth=c.depth(),encoder_cx=c.count_ops().get('cx',0),oracle_depth=full.depth(),oracle_cx=full.count_ops().get('cx',0),basis_inputs_checked=64,max_error=error)

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--witness',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=check(json.loads(a.witness.read_text()));a.report.write_text(json.dumps(r,indent=2));print(r)
