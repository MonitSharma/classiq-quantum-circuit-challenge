"""The new kernel is a phase followed by a physical ancilla permutation."""
import hashlib,json
from pathlib import Path
import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Operator
from post258_two_stage_anf import decode

def test_exact_dyadic_phase_and_permuted_kernel():
    p=Path('artifacts/193');r=json.loads((p/'kernel_recipe.json').read_text())
    c=r['class_codes'];y,x=decode(c['ylab']),decode(c['xlab'])
    care=np.array(sorted({a[0]|b<<1|(d[0]|e<<1)<<4 for a,b in y.items() for d,e in x.items()}))
    h=np.array([[(-1)**((int(w)&m).bit_count()%2) for m in range(256)] for w in care],dtype=int)
    co32=np.rint(np.array(r['co'])*32).astype(int)
    assert np.max(abs(co32/32-np.array(r['co'])))<1e-12
    truth=np.array([sum(m&~int(w)==0 for m in c['terms'])%2 for w in care])
    assert np.array_equal(h@co32,32*truth)
    kw=[11,12,13,14,4,15,16,17];mapping=r['uncompute_mapping']
    assert mapping[:12]==list(range(12)) and sorted(mapping[12:])==list(range(12,18))
    dest=[sum((int(w)>>i&1)<<kw.index(mapping[kw[i]]) for i in range(8)) for w in care]
    op=Operator(qasm2.load(p/'kernel.qasm')).data[:,care]
    want=np.zeros_like(op);want[dest,np.arange(len(care))]=(-1.)**truth
    phase=np.vdot(want,op);assert np.max(abs(op-phase/abs(phase)*want))<1e-10

def test_submission_hash_matches_exhaustive_report():
    p=Path('artifacts/193/two_stage_193.qasm')
    r=json.loads(p.with_suffix('.exhaustive.json').read_text())
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
    assert (r['depth'],r['cx_count'],r['width'],r['basis_inputs_checked'])==(193,857,18,4096)
