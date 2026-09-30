"""Concrete x4 XOR (x3 OR x5) tag: new labels, native kernel, exact inverse."""
import argparse,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from distributed_ucry import structured_ucry,verify_component
from distributed_frame_search import native
from post258_kernel_schedule import synth
from post258_two_stage_anf import decode
import post258_raw_parity_codes as raw
import two_stage_oracle as ts


def tag(x):return (x>>4&1)^((x>>3&1)|(x>>5&1))


def search(outdir,steps,seed):
    original=raw.cells
    def cc(cls,mask):
        if mask:return original(cls,mask)
        result={}
        for x,c in enumerate(cls):result.setdefault((tag(x),c),[]).append(x)
        return result
    raw.cells=cc
    try:raw.search(outdir,0,steps,seed,70,True)
    finally:raw.cells=original
    for p in outdir.glob('best_*.json'):
        r=json.loads(p.read_text());r['x_tag']='x4 XOR (x3 OR x5)';p.write_text(json.dumps(r,indent=2)+'\n')


def build(record,outdir,seeds):
    assert not outdir.exists();outdir.mkdir(parents=True);r=json.loads(record.read_text());assert r['x_tag']=='x4 XOR (x3 OR x5)'
    labs=[decode(r['ylab']),decode(r['xlab'])];es=[];rows=[]
    for side,(cls,lab) in enumerate(zip([ts.ROWCLS,ts.COLCLS],labs)):
        codes=[lab[((v>>5) if side==0 else tag(v),c)] for v,c in enumerate(cls)]
        tab=np.array([[math.pi*(c>>b&1) for c in codes] for b in range(3)])
        candidates=[]
        for seed in range(seeds):
            for sparse,opened in [(False,True),(True,False)]:
                q=structured_ucry(tab,[6,7,8],list(range(6)),seed,sparse=sparse,open_walk=opened)
                candidates.append((q.depth(),q.size(),seed,sparse,opened,q))
        choices=[(native(t[-1]),t[2:5]) for t in sorted(candidates,key=lambda t:t[:2])[:4]]
        e,settings=min(choices,key=lambda t:(t[0].depth(),t[0].size()));error=verify_component(e,tab)
        if side:
            # x4 ^= NOT(NOT(x3) AND NOT(x5)), up to relative phase.
            e.x(3);e.x(5);e.rccx(3,5,4);e.x(3);e.x(5);e.x(4)
        e=native(e);es.append(e);rows.append(dict(depth=e.depth(),settings=settings,error=error))
    phases=math.pi*np.array([sum(int(m&~w==0) for m in r['terms']) for w in range(256)],float)
    kernels=[native(synth(phases,s)) for s in range(seeds)];k=min(kernels,key=lambda q:(q.depth(),q.size()))
    enc=QuantumCircuit(18);enc.compose(es[0],ts.YW+ts.YA,inplace=True);enc.compose(es[1],ts.XW+ts.XA,inplace=True)
    q=native(enc.compose(k,[11,12,13,14,4,15,16,17]).compose(enc.inverse()));path=outdir/f'or_tag_d{q.depth()}.qasm';path.write_text(qasm2.dumps(q))
    report=dict(record=str(record),encoders=rows,kernel_depth=k.depth(),depth=q.depth(),cx=q.count_ops().get('cx',0),path=str(path));print(report,flush=True)
    (outdir/'kernel.qasm').write_text(qasm2.dumps(k));(outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    from exhaustive_verify import exhaustive
    exhaustive(path)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--steps',type=int,default=30000);p.add_argument('--seed',type=int,default=7);p.add_argument('--record',type=Path);p.add_argument('--seeds',type=int,default=24);a=p.parse_args()
    if a.record:build(a.record,a.outdir,a.seeds)
    else:search(a.outdir,a.steps,a.seed)
