"""Bounded depth-aware parity-network research, preserving all prior artifacts.

The primitive emits each requested Rz only when its exact parity is on a wire.
All CNOT changes are tracked and the final linear map is restored. This is a
heuristic construction, never an optimality claim.
"""
import argparse
import json
import math
import random
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
from distributed_ucry import walsh, change_basis, coordinates, verify_component
from distributed_frame_search import native


def synthesize(tables, seed=0):
    rng = random.Random(seed)
    coeff = walsh(tables)
    todo = {(1 << (6+t)) | m: float(coeff[t,m])
            for t in range(3) for m in range(64) if abs(coeff[t,m]) > 1e-12}
    q = QuantumCircuit(9)
    for t in range(6,9): q.rx(math.pi/2,t)
    basis = [1 << i for i in range(9)]
    times = [0]*6+[1]*3
    def emit_ready():
        for i,p in enumerate(basis):
            if p in todo:
                q.rz(todo.pop(p),i); times[i]+=1
    def cx(a,b):
        q.cx(a,b);basis[b]^=basis[a]
        times[a]=times[b]=max(times[a],times[b])+1
        emit_ready()
    emit_ready()
    while todo:
        # Pick the parity whose balanced reduction can complete earliest.
        choices=[]
        for p in todo:
            mask=coordinates(p,basis)
            active=[i for i in range(9) if mask>>i&1]
            ts=sorted(times[i] for i in active)
            while len(ts)>1:
                x,y=ts.pop(0),ts.pop(0)
                ts.append(max(x,y)+1);ts.sort()
            choices.append((ts[0]+rng.random()*2, len(active), p, active))
        _,_,target,active=min(choices)
        while len(active)>1:
            # Choose a reduction pair that also shortens other pending parities.
            pending=[coordinates(p,basis) for p in todo]
            opts=[]
            for a in active:
                for b in active:
                    if a==b: continue
                    gain=sum((1 if m>>a&1 else -1) for m in pending if m>>b&1)
                    hit=int((basis[a]^basis[b]) in todo)
                    time=max(times[a],times[b])+1
                    opts.append((time-0.025*gain-0.5*hit+rng.random()*0.3,a,b))
            _,a,b=min(opts)
            cx(a,b)
            active.remove(a)
        assert target not in todo
    q.compose(change_basis(tuple(basis),tuple(1<<i for i in range(9))),inplace=True)
    for t in range(6,9): q.rx(-math.pi/2,t)
    return q


def run(outdir,seeds):
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    data=json.loads(Path('artifacts/post258_lift_probe.json').read_text())
    rows=[]
    for side in data:
        record=side['results'][0]
        a=np.array([v[0] for v in record['lifts']])*math.pi
        b=np.array([v[1] for v in record['lifts']])*math.pi
        for stage,table in enumerate([a,b-a,-b]):
            best=None
            for seed in range(seeds):
                raw=synthesize(table,seed)
                q=native(raw)
                score=(q.depth(),q.count_ops().get('cx',0))
                if best is None or score < best[0]: best=(score,q,seed)
            score,q,seed=best
            error=verify_component(q,table)
            path=outdir/f'{side["side"]}{stage}_d{score[0]}.qasm'
            path.write_text(qasm2.dumps(q))
            row=dict(side=side['side'],stage=stage,seed=seed,depth=score[0],cx=score[1],error=error,path=str(path))
            rows.append(row);print(row,flush=True)
    (outdir/'report.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=4)
    a=p.parse_args();run(a.outdir,a.seeds)
