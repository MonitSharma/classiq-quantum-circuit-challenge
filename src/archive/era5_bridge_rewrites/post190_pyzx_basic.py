"""Run PyZX full reduction with extracted SWAPs expanded to basic gates."""
import json
from pathlib import Path
import pyzx as zx
from qiskit import qasm2
from qiskit.quantum_info import Operator
from distributed_frame_search import native

def equiv(a,b):
    x,y=Operator(a).data,Operator(b).data
    i,j=divmod(abs(x).argmax(),x.shape[1]);p=x[i,j]/y[i,j]
    return bool(max(abs(x-p*y).flat)<1e-8)

def run(out):
    assert not out.exists();out.mkdir(parents=True)
    source=Path('artifacts/190/two_stage_190.qasm');base=qasm2.load(source)
    c=zx.Circuit.from_qasm(source.read_text());g=c.to_graph();zx.full_reduce(g)
    extracted=zx.extract_circuit(g).to_basic_gates();p=out/'reduced.qasm';p.write_text(extracted.to_qasm())
    q=native(qasm2.load(p));row=dict(depth=q.depth(),cx=q.count_ops().get('cx',0),equiv=equiv(q,base));
    if row['equiv']:p2=out/f'oracle_d{row["depth"]}_cx{row["cx"]}.qasm';p2.write_text(qasm2.dumps(q));row['path']=str(p2)
    (out/'report.json').write_text(json.dumps(row,indent=2)+'\n');print(row)
if __name__=='__main__':run(Path('artifacts/post190_pyzx_basic_v1'))
