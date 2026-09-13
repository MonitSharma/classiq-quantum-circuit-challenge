"""Relax full controlled-Ry equivalence at the lookup boundary.

H D H gives the same loaded bits as controlled Ry(pi*f), up to input phase.
Trailing data-to-target CXs become CZs after the final H, so removing them
also changes only a diagonal phase. The exact inverse cancels both changes.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from distributed_ucry import structured_ucry
from distributed_frame_search import native
from post258_two_stage_anf import decode
import two_stage_oracle as ts


def relative(table,seed):
    q=structured_ucry(table,[6,7,8],list(range(6)),seed,sparse=False,open_walk=True)
    data=list(q.data);assert all(i.operation.name=='rx' for i in data[:3]+data[-3:])
    body=data[3:-3];removed=[]
    while body and body[-1].operation.name=='cx':
        inst=body[-1];a,b=[q.find_bit(v).index for v in inst.qubits]
        if a>=6 or b<6:break
        removed.append((a,b));body.pop()
    out=QuantumCircuit(9)
    for b in [6,7,8]:out.h(b)
    for inst in body:out.append(inst.operation,[q.find_bit(v).index for v in inst.qubits])
    for b in [6,7,8]:out.h(b)
    return native(out),removed


def run(outdir,seeds):
    assert not outdir.exists();outdir.mkdir(parents=True);r=json.loads(Path('artifacts/224/class_codes.json').read_text());es=[];rows=[]
    for side,cls,mask,lab in [(0,ts.ROWCLS,32,decode(r['ylab'])),(1,ts.COLCLS,48,decode(r['xlab']))]:
        codes=[lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)]
        table=np.array([[math.pi*(c>>b&1) for c in codes] for b in range(3)]);options=[]
        for seed in range(seeds):
            q,removed=relative(table,seed);options.append((q.depth(),q.size(),seed,q,removed))
        _,_,seed,e,removed=min(options,key=lambda t:t[:2]);errors=[]
        for v in range(64):
            state=Statevector.from_int(v,512).evolve(e).data;w=v|(codes[v]<<6);phase=state[w]/abs(state[w]);want=np.zeros(512,complex);want[w]=phase;errors.append(float(np.max(abs(state-want))))
        assert max(errors)<1e-10
        if side:e.cx(5,4)
        es.append(e);rows.append(dict(side=side,seed=seed,depth=e.depth(),removed=removed,subspace_error=max(errors)));print(rows[-1],flush=True)
        (outdir/f'encoder_{side}.qasm').write_text(qasm2.dumps(e))
    enc=QuantumCircuit(18);enc.compose(es[0],ts.YW+ts.YA,inplace=True);enc.compose(es[1],ts.XW+ts.XA,inplace=True);k=qasm2.load('artifacts/224/kernel.qasm')
    q=native(enc.compose(k,[11,12,13,14,4,15,16,17]).compose(enc.inverse()));path=outdir/f'relative_lookup_d{q.depth()}.qasm';path.write_text(qasm2.dumps(q))
    report=dict(encoders=rows,depth=q.depth(),cx=q.count_ops().get('cx',0),path=str(path));print(report,flush=True)
    (outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    from exhaustive_verify import exhaustive
    exhaustive(path)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=32);a=p.parse_args();run(a.outdir,a.seeds)
