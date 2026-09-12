"""Regression checks for phase conventions and nonlinear kernel rewrites."""
import sys
from pathlib import Path
import numpy as np
from qiskit.quantum_info import Operator
from qiskit.circuit.library import PhaseGate
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from post258_aam_fixed import fixed_aam
from post258_kernel_nonlinear import transform,terms
from post258_kernel_schedule import synth
from distributed_frame_search import native


def test_numeric_phase_wrap_preserves_three_pi_over_two():
    q=fixed_aam([[1]], [3*np.pi/2],section_size=1)
    assert np.max(abs(Operator(q).data-Operator(PhaseGate(3*np.pi/2)).data))<1e-12


def test_polynomial_conjugations_on_all_inputs():
    rng=np.random.default_rng(243)
    poly=sum(1<<int(m) for m in rng.choice(256,40,replace=False))
    for controls,target in [((0,),5),((1,3),7),((2,6),0)]:
        new=transform(poly,controls,target)
        for w in range(256):
            v=w ^ ((int(all(w>>c&1 for c in controls)))<<target)
            old=sum(m&~v==0 for m in terms(poly))%2
            got=sum(m&~w==0 for m in terms(new))%2
            assert old==got


def test_depth_scheduler_arbitrary_angles_all_basis_states():
    rng=np.random.default_rng(243)
    # Sparse parity phases with arbitrary signs and non-Clifford angles.
    phases=np.zeros(256)
    for m,angle in zip([1,3,12,27,65,133,255],rng.uniform(-5,5,7)):
        phases+=angle*np.array([(-1)**((m&w).bit_count()%2) for w in range(256)])
    q=native(synth(phases,28));op=Operator(q).data;want=np.diag(np.exp(1j*phases))
    phase=np.vdot(want,op)
    assert np.max(abs(op-phase/abs(phase)*want))<1e-10
