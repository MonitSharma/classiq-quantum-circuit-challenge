"""Compose free-placement semantic encoders with the protected phase function.

Remove the saved kernel's physical bit permutation explicitly before remapping
its eight inputs. Then use the actual encoder inverse. No output layout is
assumed to be a physical gate.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from distributed_frame_search import native
from build_two_stage_196 import encoders
from post190_register_compose import WIRES
from post190_degree_rank_bound import targets
from post190_semantic_register import verify,INPUTS


def diagonal_kernel():
    q=qasm2.load('artifacts/190/kernel.qasm');op=Operator(q).data
    dest=np.argmax(abs(op),axis=0)
    assert dest[0]==0 and np.all(abs(op[dest,np.arange(256)])>1-1e-10)
    image=[int(dest[1<<i]).bit_length()-1 for i in range(8)]
    assert sorted(image)==list(range(8))
    assert all(int(dest[x])==sum(((x>>i)&1)<<image[i] for i in range(8)) for x in range(256))
    at=[image.index(i) for i in range(8)]
    for i in range(8):
        j=at.index(i)
        if i!=j:q.swap(i,j);at[i],at[j]=at[j],at[i]
    q=native(q);m=Operator(q).data
    assert np.max(abs(m-np.diag(np.diag(m))))<1e-10
    return q


def compose(replacements):
    codes=json.loads(Path('artifacts/190/class_codes.json').read_text());base=encoders(codes,298,506)
    e=QuantumCircuit(18);kernel_wires=[];checks={}
    for side in ('y','x'):
        ws=WIRES[side]
        if side in replacements:q,places=replacements[side]
        else:
            q=QuantumCircuit(9);local={w:i for i,w in enumerate(ws)}
            for inst in base.data:
                physical=[base.find_bit(v).index for v in inst.qubits]
                if set(physical)<=set(ws):q.append(inst.operation,[local[v] for v in physical])
            places=[6,7,8,5 if side=='y' else 4]
        ts=targets()[side];goals=[sum(int(t[x])<<x for x in range(64)) for t in ts]+[INPUTS[5] if side=='y' else INPUTS[4]^INPUTS[5]]
        checks[side]=verify(q,places,goals)
        e.compose(q,ws,inplace=True);kernel_wires.extend(ws[i] for i in [places[3],*places[:3]])
    q=native(e.compose(diagonal_kernel(),kernel_wires).compose(e.inverse()))
    return q,checks

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--x',type=Path);p.add_argument('--y',type=Path);p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();assert not a.outdir.exists();a.outdir.mkdir(parents=True)
    replacements={}
    for side,folder in [('x',a.x),('y',a.y)]:
        if folder:
            report=json.loads((folder/'report.json').read_text());replacements[side]=(qasm2.load(folder/'encoder.qasm'),report['best']['outputs'])
    q,checks=compose(replacements);text=qasm2.dumps(q);path=a.outdir/'oracle.qasm';path.write_text(text)
    from exhaustive_verify import exhaustive
    exhaustive(path)
    r=dict(depth=q.depth(),cx=q.count_ops().get('cx',0),width=q.num_qubits,sha256=hashlib.sha256(text.encode()).hexdigest(),encoders=checks)
    (a.outdir/'report.json').write_text(json.dumps(r,indent=2));print(r)
