"""Verify and integrate integer-lifted two-stage kernels with exact inverses."""
import argparse,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from depth_parity_network import synth
from distributed_ucry import structured_ucry,verify_component
from distributed_frame_search import native
from post258_two_stage_anf import decode
import two_stage_oracle as ts


def run(record_path,outdir,seeds,kernel_file=None):
    assert not outdir.exists();outdir.mkdir(parents=True)
    rec=json.loads(record_path.read_text());yl=decode(rec['ylab']);xl=decode(rec['xlab'])
    lifted=np.array([sum(int(m&~w==0) for m in rec['terms']) for w in range(256)],float)
    truth=np.array(ts.kernel_table(yl,xl,fill=0),float)
    variants={'integer_anf':math.pi*lifted,'boolean_anf':math.pi*(lifted%2),'zero_fill':math.pi*truth}
    options=[]
    if kernel_file is not None:
        q=qasm2.load(kernel_file)
        options.append((q.depth(),q.size(),'integer_anf',-1,q,math.pi*lifted))
    for variant,phases in (variants.items() if kernel_file is None else []):
        for seed in range(seeds):
            q=native(synth(phases,8,seed))
            options.append((q.depth(),q.size(),variant,seed,q,phases))
        best=min(options,key=lambda r:r[:2]);print('kernel best',best[:4],flush=True)
    depth,_,variant,kernel_seed,k,phases=min(options,key=lambda r:r[:2])
    op=Operator(qasm2.loads(qasm2.dumps(k))).data;want=np.diag(np.exp(1j*phases));phase=np.vdot(want,op);error=float(np.max(abs(op-phase/abs(phase)*want)))
    assert error<1e-10
    (outdir/f'kernel_d{depth}.qasm').write_text(qasm2.dumps(k))
    _,_,yt,xt=ts.code_tables(yl,xl)
    encoder=QuantumCircuit(18);checks=[]
    for table,wires in [(yt,ts.YW+ts.YA),(xt,ts.XW+ts.XA)]:
        shortlist=[]
        for seed in range(24):
            for sparse,opened in [(False,True),(True,False)]:
                q=structured_ucry(table,[6,7,8],list(range(6)),seed,sparse=sparse,open_walk=opened)
                shortlist.append((q.depth(),q.size(),seed,sparse,opened,q))
        shortlist.sort(key=lambda r:r[:2]);choices=[]
        for _,_,seed,sparse,opened,q in shortlist[:3]:
            q=native(q);choices.append((q.depth(),q.size(),seed,sparse,opened,q))
        d,_,sd,sp,ow,q=min(choices,key=lambda r:r[:2]);err=verify_component(q,table)
        checks.append(dict(depth=d,seed=sd,sparse=sp,open_walk=ow,error=err))
        encoder.compose(q,wires,inplace=True)
    q=encoder.copy();q.compose(k,ts.KERNEL_WIRES,inplace=True);q.compose(encoder.inverse(),inplace=True);q=native(q)
    path=outdir/f'two_stage_d{q.depth()}.qasm';path.write_text(qasm2.dumps(q))
    report=dict(record=str(record_path),kernel=dict(depth=depth,variant=variant,seed=kernel_seed,error=error,cx=k.count_ops().get('cx',0)),components=checks,depth=q.depth(),cx=q.count_ops().get('cx',0),path=str(path))
    (outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
    from exhaustive_verify import exhaustive
    exhaustive(path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=12);p.add_argument('--kernel-file',type=Path);a=p.parse_args();run(a.record,a.outdir,a.seeds,a.kernel_file)
