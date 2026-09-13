"""Regression checks for the new preconditioning screen's ranking data."""
import numpy as np
from post196_nonlinear_loader_search import bounds,pre_circuit
from post196_frame_balance import loader_floor
from qiskit.quantum_info import Statevector

def test_batched_frame_bound_matches_scalar():
 rng=np.random.default_rng(196)
 values=rng.integers(0,8,size=(8,64))
 costs,_,_=bounds(values)
 for v,c in zip(values,costs):
  table=((v[None,:]>>np.arange(3)[:,None])&1).astype(float)
  assert int(c)==loader_floor(table)[0]

def test_negative_control_preconditioner_preserves_raw_tag():
 for side,tag in [(0,5),(1,4)]:
  seq=[(0,1,2,3),(2,3,0,1)]
  q=pre_circuit(side,seq)
  for v in range(64):
   w=v^((((v>>5)&1)<<4) if side else 0)
   raw=(w>>tag)&1
   for a,b,t,pol in seq:
    w^=((((w>>a)&1)^(pol&1))&(((w>>b)&1)^(pol>>1)))<<t
   s=Statevector.from_int(v,512).evolve(q).data
   assert abs(s[w])>1-1e-12
   assert (w>>tag)&1==raw
