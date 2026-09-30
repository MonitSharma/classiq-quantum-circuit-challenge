import sys,json
sys.path.insert(0,'src')
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from distributed_frame_search import native
from search import logo
q=QuantumCircuit(18)
for w in range(18):q.rz(.37,w)
a=native(q)
e=QuantumCircuit(11)
for t in [(0,1,6),(2,3,7),(4,5,8),(6,7,9),(9,8,10)]:e.rccx(*t)
e=native(e);err=0.
for x in range(64):
 v=Statevector.from_int(x,2048).evolve(e).data
 support=np.flatnonzero(abs(v)>1e-10);assert len(support)==1
 assert ((int(support[0])>>10)&1)==int(x==63)
M=np.array([[logo(x,y) for x in range(64)] for y in range(64)],dtype=np.uint8)
r=0
for c in range(64):
 p=next((i for i in range(r,64) if M[i,c]),None)
 if p is None:continue
 M[[r,p]]=M[[p,r]]
 for i in range(64):
  if i!=r and M[i,c]:M[i]^=M[r]
 r+=1
rep=dict(parallel_rz_depth=a.depth(),parallel_rz_count=a.size(),full_six_input_AND_compute_depth=e.depth(),AND_compute_cx=e.count_ops().get('cx',0),AND_nodes=5,AND_basis_inputs_checked=64,logo_gf2_matrix_rank=r)
print(rep)
open('artifacts/post190_side_analysis_audit/counterexamples.json','w').write(json.dumps(rep,indent=2))
