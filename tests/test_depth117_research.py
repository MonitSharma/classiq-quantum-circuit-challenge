"""Independent correctness checks for the depth-117 research tools."""
import itertools
from pathlib import Path
import sys
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/post151_sa'))
from rewrite117 import rewrite
from modsupport117 import solve_mod
from local117 import synth
from window_sat117 import bounded,decode

def circuit(ops,wires):
 q=QuantumCircuit(len(wires));ids={w:i for i,w in enumerate(wires)}
 for name,ws,u in ops:
  if name=='cx':q.cx(ids[ws[0]],ids[ws[1]])
  else:q.unitary(u,[ids[ws[0]]])
 return q

def test_bridge_all_wire_assignments_and_both_directions():
 for a,b,c in itertools.permutations(range(3)):
  for ws in [[(a,b),(b,c)],[(b,c),(a,b)]]:
   ops=[('cx',v,None) for v in ws]
   for d in ['left','right']:
    changed=rewrite(ops,(0,1,d))
    assert Operator(circuit(ops,range(3))).equiv(Operator(circuit(changed,range(3))))

def test_modular_solver_matches_exhaustive_small_systems():
 rng=np.random.default_rng(117)
 for modulus in [2,4,8]:
  xs=np.array(list(itertools.product(range(modulus),repeat=3)))
  for _ in range(30):
   a=rng.integers(0,modulus,(4,3));b=rng.integers(0,modulus,4)
   feasible=np.any(np.all((xs@a.T-b)%modulus==0,axis=1));got=solve_mod(a,b,modulus)
   assert (got is not None)==feasible
   if got is not None:assert np.all((a@got-b)%modulus==0)

def test_three_wire_phase_resynthesis_as_full_unitary():
 ops=[('cx',(0,1),None),('u3',(1,),np.diag([1,np.exp(.37j)])),('cx',(1,2),None),('u3',(2,),np.diag([1,np.exp(-.19j)])),('cx',(0,1),None)]
 for variant in range(3):
  new=synth(ops,list(range(len(ops))),(0,1,2),variant)
  assert Operator(circuit(ops,range(3))).equiv(Operator(circuit(new,range(3))),atol=1e-10)

def test_sat_replacement_positive_and_negative_controls():
 # A parity phase with identity output requires CX, phase, CX on two wires.
 goal=[1,2];angles={3:.27}
 yes=bounded(2,goal,angles,3,{(0,1,1),(0,1,3)},10)
 assert yes['status']=='SAT'
 ops=decode(yes,[0,1],goal,angles,3)
 ref=QuantumCircuit(2);ref.cx(0,1);ref.p(.27,1);ref.cx(0,1)
 assert Operator(ref).equiv(Operator(circuit(ops,range(2))),atol=1e-10)
 assert bounded(2,goal,angles,2,set(),10)['status']=='UNSAT'
