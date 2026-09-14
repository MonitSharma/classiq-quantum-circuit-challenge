"""Independent checks for new descriptor witnesses and direct-oracle template."""
import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from distributed_frame_search import native
from post190_direct_boolean_template import solve,assemble_oracle
from two_stage_oracle import ROWCLS,COLCLS

def test_degree_four_witnesses_separate_every_class():
 rows=json.loads(Path('artifacts/post190_split_degree4_v1/report.json').read_text())
 for r,classes in zip(rows,[ROWCLS,COLCLS]):
  assert r['status']=='sat'
  for v in range(64):
   actual=0
   for m,c in enumerate(r['anf']):
    if m&~v==0:actual^=c
   assert actual==r['codes'][v]
  assert max(m.bit_count() for m,c in enumerate(r['anf']) if c)==4
  for a in range(64):
   for b in range(a):
    if ((a&r['raw_mask']).bit_count()%2)==((b&r['raw_mask']).bit_count()%2) and classes[a]!=classes[b]:assert r['codes'][a]!=r['codes'][b]

def test_direct_template_positive_control():
 # The first fixed stage already computes y4 AND y5 in physical wire 17.
 r,ops=solve(list(range(16))+[1024,2048,3072,4095],6,3,10,
             target_function=lambda x,y:bool(y&16 and y&32),force_identity_tail=True)
 assert r['status']=='sat'
 words=np.arange(4096,dtype=np.int64)
 for kind,w in ops:
  if kind=='cx':a,b=w;words^=(words>>a&1)<<b
  else:a,b,t=w;words^=((words>>a&1)&(words>>b&1))<<t
 original=np.arange(4096)
 assert np.array_equal(words>>17&1,(original>>10&1)&(original>>11&1))
 q=assemble_oracle(ops)
 assert q.depth()<=139 and set(q.count_ops())<={'u3','cx'}

def test_rccx_stage_depth_and_phase_cleanup():
 q=QuantumCircuit(18)
 for i in range(6):q.rccx(2*i,2*i+1,12+i)
 assert native(q).depth()<=9
 assert 2*(6*9+5*3)+1==139
 e=QuantumCircuit(3);e.rccx(0,1,2);q=e.copy();q.z(2);q.compose(e.inverse(),inplace=True)
 want=np.diag([(-1)**(((v>>2)&1)^((v&1)&((v>>1)&1))) for v in range(8)])
 assert Operator(native(q)).equiv(Operator(want))
