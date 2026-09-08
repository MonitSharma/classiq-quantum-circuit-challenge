"""Independent verifier of serialized u3/cx QASM against the geometric specification."""
import sys,json,re,hashlib,time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit_aer import AerSimulator
from search import MASK,logo

def verify(path,tests=5):
 source=Path(path).read_text();q=qasm2.loads(source)
 assert 12<=q.num_qubits<=18
 assert set(q.count_ops())<={'u3','cx'}
 assert len(q.qregs)==1 and q.qregs[0].name=='q'
 rng=np.random.default_rng(20260908);backend=AerSimulator(method='statevector',max_parallel_threads=4)
 target=np.array([-1 if logo(x,y) else 1 for y in range(64) for x in range(64)])
 maxerr=leak=normerr=0.;globalphase=None
 for k in range(tests):
  # Independent amplitudes and phases, all coordinates supported.
  a=rng.normal(size=4096)+1j*rng.normal(size=4096);a/=np.linalg.norm(a)
  initial=np.zeros(1<<q.num_qubits,complex);initial[:4096]=a
  qc=QuantumCircuit(q.num_qubits);qc.set_statevector(initial);qc.compose(q,inplace=True);qc.save_statevector()
  v=np.asarray(backend.run(qc).result().get_statevector())
  expect=initial.copy();expect[:4096]*=target
  overlap=np.vdot(expect,v)
  if globalphase is None:globalphase=overlap/abs(overlap)
  err=float(np.max(np.abs(v-globalphase*expect)))
  maxerr=max(maxerr,err);leak=max(leak,float(np.max(np.abs(v[4096:]),initial=0)))
  normerr=max(normerr,float(abs(np.vdot(v,v).real-1)))
  print('state',k,'error',err,flush=True)
 assert maxerr<1e-10 and leak<1e-10 and normerr<1e-10,(maxerr,leak,normerr)
 report=dict(qasm=str(Path(path).resolve()),sha256=hashlib.sha256(source.encode()).hexdigest(),width=q.num_qubits,depth=q.depth(),cx_count=q.count_ops().get('cx',0),random_dense_states=tests,max_error=maxerr,ancilla_error=leak,normalization_error=normerr,verification='Dense random inputs supported on all 4096 coordinates; probabilistic numerical check, not exhaustive operator proof')
 Path(path).with_suffix('.verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
 return report
if __name__=='__main__':verify(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 5)
