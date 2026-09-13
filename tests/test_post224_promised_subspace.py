"""Independent checks for clean-helper scheduling and GF(2) elimination."""
import sys
from pathlib import Path
import numpy as np
from qiskit.quantum_info import Operator
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from post224_clean_parity import synth_clean
from distributed_frame_search import native
from post224_nonlinear_tags import null_basis


def test_clean_helper_phase_on_all_promised_columns():
    phases=np.array([0.17,-0.3,0.22,0.41,-0.72,0.19,0.81,-0.11])
    for seed in [0,7]:
        op=Operator(native(synth_clean(phases,2,seed))).data
        wanted=np.zeros((32,8),complex)
        for i,p in enumerate(phases):wanted[i,i]=np.exp(1j*p)
        phase=np.vdot(wanted,op[:,:8]);phase/=abs(phase)
        assert np.max(abs(op[:,:8]-phase*wanted))<1e-12


def test_null_basis_against_complete_enumeration():
    rows=[0b001111,0b101010,0b110101]
    basis=null_basis(rows,6);span={0}
    for b in basis:span|={v^b for v in list(span)}
    wanted={v for v in range(64) if all((v&r).bit_count()%2==0 for r in rows)}
    assert span==wanted
