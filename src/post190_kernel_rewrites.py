"""Try exact local rewrite stacks on the protected 190 kernel and composition."""
import json
from pathlib import Path
from qiskit import qasm2
from qiskit.quantum_info import Operator
from distributed_frame_search import native
from build_two_stage_196 import encoders, KERNEL_WIRES

def same_up_to_global(a, b):
    x, y = Operator(a).data, Operator(b).data
    i, j = divmod(abs(x).argmax(), x.shape[1]); phase = x[i,j]/y[i,j]
    return bool(max(abs(x-phase*y).flat) < 1e-9)

def run(out):
    assert not out.exists(); out.mkdir(parents=True)
    source = Path('artifacts/190/kernel.qasm'); base = qasm2.load(source)
    rows=[]
    # Pytket rewrites
    try:
        from pytket.qasm import circuit_from_qasm, circuit_to_qasm
        from pytket import passes
        for name in ('FullPeepholeOptimise','CliffordSimp','OptimisePhaseGadgets','PauliSimp','GreedyPauliSimp'):
            c=circuit_from_qasm(str(source)); getattr(passes,name)().apply(c)
            p=out/(name+'.qasm'); circuit_to_qasm(c,str(p)); q=native(qasm2.load(p))
            rows.append(dict(method=name,depth=q.depth(),cx=q.count_ops().get('cx',0),equiv=same_up_to_global(q,base)))
    except Exception as e: rows.append(dict(method='pytket_error',error=repr(e)))
    # PyZX rewrite
    try:
        import pyzx as zx
        c=zx.Circuit.from_qasm(source.read_text()); g=c.to_graph(); zx.full_reduce(g); q=native(qasm2.loads(zx.extract_circuit(g).to_qasm()))
        rows.append(dict(method='pyzx_full_reduce',depth=q.depth(),cx=q.count_ops().get('cx',0),equiv=same_up_to_global(q,base)))
    except Exception as e: rows.append(dict(method='pyzx_error',error=repr(e)))
    codes=json.loads(Path('artifacts/190/class_codes.json').read_text()); enc=encoders(codes,298,506)
    full=[]
    for row in rows:
        if not row.get('equiv'): continue
        p=out/(row['method']+'.qasm'); q=qasm2.load(p) if p.exists() else None
        if q is None and row['method']=='pyzx_full_reduce':
            continue
        if q is not None:
            fullq=native(enc.compose(q,KERNEL_WIRES).compose(enc.inverse()))
            row.update(full_depth=fullq.depth(),full_cx=fullq.count_ops().get('cx',0))
    (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(rows,indent=2))
if __name__=='__main__': run(Path('artifacts/post190_kernel_rewrites_v2'))
