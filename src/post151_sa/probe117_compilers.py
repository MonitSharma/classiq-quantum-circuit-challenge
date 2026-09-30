"""Bounded compiler probes on the 117-depth oracle; no implicit layouts."""
import argparse,json,time
from pathlib import Path
from pytket.qasm import circuit_from_qasm,circuit_to_qasm_str
from pytket.circuit import OpType
from pytket.passes import AutoRebase,FullPeepholeOptimise,CliffordSimp,PauliSimp,RemoveRedundancies,SynthesiseTket
from pytket.transform import PauliSynthStrat
from qiskit import qasm2,transpile
parser=argparse.ArgumentParser()
parser.add_argument('source',nargs='?',type=Path,default=Path('artifacts/117/conditional_loader_117_cx577.qasm'))
parser.add_argument('output',nargs='?',type=Path,default=Path('artifacts/rewrite117_20260922/compilers'))
args=parser.parse_args()
src=args.source;out=args.output;out.mkdir(parents=True,exist_ok=True)
rows=[]
for name,ps in [('clifford',[CliffordSimp(False)]),('peephole',[FullPeepholeOptimise(False)]),('paulipair',[PauliSimp(PauliSynthStrat.Pairwise)]),('paulisets',[PauliSimp(PauliSynthStrat.Sets)])]:
 t=time.monotonic();c=circuit_from_qasm(str(src))
 if name.startswith('pauli'): AutoRebase({OpType.CX,OpType.Rz,OpType.Rx,OpType.H},False).apply(c)
 for p in ps+[RemoveRedundancies(),AutoRebase({OpType.CX,OpType.U3},False)]: p.apply(c)
 assert all(k==v for k,v in c.implicit_qubit_permutation().items())
 q=qasm2.loads(circuit_to_qasm_str(c));q=transpile(q,basis_gates=['u3','cx'],optimization_level=1,qubits_initially_zero=False)
 assert q.layout is None
 path=out/(name+'.qasm');path.write_text(qasm2.dumps(q));r=dict(name=name,depth=q.depth(),cx=q.count_ops().get('cx',0),seconds=time.monotonic()-t);rows.append(r);print(r,flush=True)
q=transpile(qasm2.load(src),basis_gates=['u3','cx'],optimization_level=3,qubits_initially_zero=False,seed_transpiler=116)
assert q.layout is None
(out/'qiskit_o3.qasm').write_text(qasm2.dumps(q))
rows.append(dict(name='qiskit_o3',depth=q.depth(),cx=q.count_ops().get('cx',0)))
print(rows[-1],flush=True)
(out/'report.json').write_text(json.dumps(rows,indent=2))
