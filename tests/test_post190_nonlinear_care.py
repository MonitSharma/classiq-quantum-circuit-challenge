"""Small exhaustive checks for nonlinear phase-conjugation search contracts."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from post190_nonlinear_care import care_truth,conjugator,permute
from post258_two_stage_anf import decode
from qiskit.quantum_info import Operator
import two_stage_oracle as ts


def test_care_truth_matches_all_coordinate_inputs():
 codes=json.loads(Path('artifacts/190/class_codes.json').read_text())
 care,truth=care_truth(codes);lookup=dict(zip(care,truth));seen=set()
 yl,xl=decode(codes['ylab']),decode(codes['xlab'])
 for y in range(64):
  yt=(y&32).bit_count()%2;yc=yl[(yt,ts.ROWCLS[y])]
  for x in range(64):
   xt=(x&48).bit_count()%2;xc=xl[(xt,ts.COLCLS[x])]
   w=yt|(yc<<1)|(xt<<4)|(xc<<5);seen.add(w)
   assert lookup[w]==ts.logo(x,y)
 assert seen==set(care) and len(care)==182


def test_open_control_relative_phase_conjugation():
 words=np.arange(256);angles=np.sin(words)*.3
 for move in [(0,3,5,a,b) for a in (0,1) for b in (0,1)]:
  c=Operator(conjugator(move)).data;p=permute(words,move)
  assert np.array_equal(np.argmax(abs(c),axis=0),p)
  assert np.array_equal(permute(p,move),words)
  got=c.conj().T@np.diag(np.exp(1j*angles[p]))@c
  assert np.max(abs(got-np.diag(np.exp(1j*angles))))<1e-12


def test_phase_recipe_units_and_reachable_domain():
 from post190_reachable_lift_beam import reachable,phase_values,coeff
 from qiskit import qasm2
 codes=json.loads(Path('artifacts/190/class_codes.json').read_text())
 care,truth=care_truth(codes)
 assert reachable(codes)==care.tolist()
 values=phase_values(Path('artifacts/190/kernel.qasm'))
 expected=np.array(json.loads(Path('artifacts/193_cx853/phase_search_recipe.json').read_text())['co'])*np.pi
 assert np.max(abs(coeff(values)-expected))<1e-12
 assert np.max(abs(np.exp(1j*np.pi*values[care])-np.exp(1j*np.pi*truth)))<1e-12
 op=Operator(qasm2.load('artifacts/190/kernel.qasm')).data
 entries=op[np.argmax(abs(op),axis=0),np.arange(256)]
 expected=np.exp(1j*np.pi*values);phase=np.vdot(expected,entries);phase/=abs(phase)
 assert np.max(abs(entries-phase*expected))<1e-12


def test_fixed_boundary_window():
 from post190_window_phase import polynomial,finish_to
 from qiskit import QuantumCircuit
 from distributed_frame_search import native
 from post218_beam_phase import psynth
 q=QuantumCircuit(8);q.cx(1,3);q.rz(.7,3);q.cx(3,6);q.rz(-.13,6);q.cx(0,5)
 q=native(q);targets,goal,phase=polynomial(q)
 def finalize(c,basis):
  r=finish_to(c,basis,goal)
  return (r.depth(),r.size()),r
 r=psynth(8,targets,global_phase=phase,finalize=finalize,beam=8,branch=4)
 assert np.max(abs(Operator(q).data-Operator(r).data))<1e-12
