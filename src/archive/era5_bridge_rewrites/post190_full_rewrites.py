"""Try exact whole-oracle Pytket rewrites on the protected 190 QASM."""
import json
from pathlib import Path
from qiskit import qasm2
from qiskit.quantum_info import Operator
from distributed_frame_search import native

def equiv(a,b):
    x,y=Operator(a).data,Operator(b).data
    i,j=divmod(abs(x).argmax(),x.shape[1]); p=x[i,j]/y[i,j]
    return bool(max(abs(x-p*y).flat)<1e-8)

def run(out):
    assert not out.exists();out.mkdir(parents=True)
    source=Path('artifacts/190/two_stage_190.qasm'); base=qasm2.load(source); rows=[]
    try:
        from pytket.qasm import circuit_from_qasm,circuit_to_qasm
        from pytket import passes
        for name in ('FullPeepholeOptimise','CliffordSimp','OptimisePhaseGadgets','PauliSimp'):
            try:
                c=circuit_from_qasm(str(source));getattr(passes,name)().apply(c)
                p=out/(name+'.qasm');circuit_to_qasm(c,str(p));q=native(qasm2.load(p))
                rows.append(dict(method=name,depth=q.depth(),cx=q.count_ops().get('cx',0),equiv=equiv(q,base)))
            except Exception as e: rows.append(dict(method=name,error=repr(e)))
    except Exception as e: rows.append(dict(method='pytket_import',error=repr(e)))
    (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':run(Path('artifacts/post190_full_rewrites_v1'))
