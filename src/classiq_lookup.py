from classiq import *
from pathlib import Path
from radius import radius
from qiskit import qasm2,transpile
@qperm
def lookup(table: CArray[CInt], y: Const[QNum], r: Output[QNum]):
 r |= table[y]
@qfunc
def main(y:Output[QNum[6]],r:Output[QNum[3]]):
 allocate(y);hadamard_transform(y)
 lookup([radius(y) for y in range(64)],y,r)
model=create_model(main,constraints=Constraints(max_width=12,optimization_parameter=OptimizationParameter.DEPTH))
write_qmod(model,'artifacts/lookup')
if __name__=='__main__':
 p=synthesize(model);raw=export(p,TargetLanguage.QASM2);Path('artifacts/lookup_raw.qasm').write_text(raw)
 lines=raw.splitlines();prep=[i for i,l in enumerate(lines) if l.lstrip().startswith('hadamard_transform') and 'q[' in l]
 assert len(prep)==1
 q=qasm2.loads('\n'.join(l for i,l in enumerate(lines) if i not in prep),custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
 q=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
 print(q.depth(),q.count_ops(),flush=True);Path('artifacts/lookup.qasm').write_text(qasm2.dumps(q))
