"""Depth-aware scheduling variants for the eight-wire two-stage phase kernel."""
import argparse,json,math,random
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from depth_parity_network import walsh,restore,_coords
from distributed_frame_search import native


def synth(phases,seed):
    n=(len(phases)-1).bit_length();assert len(phases)==1<<n
    rng=random.Random(seed);co=walsh(phases)
    todo={m:float(co[m]) for m in range(1,1<<n) if abs(co[m])>1e-12}
    q=QuantumCircuit(n);q.global_phase=float(co[0]);basis=[1<<i for i in range(n)];times=[0]*n
    gain_weight=rng.uniform(3,12);look_weight=rng.uniform(0.2,2);time_weight=rng.uniform(0.1,2)
    def flush():
        for w,m in enumerate(basis):
            if m in todo:q.rz(-2*todo.pop(m),w);times[w]+=1
    def cx(a,b):
        q.cx(a,b);basis[b]^=basis[a];times[a]=times[b]=max(times[a],times[b])+1
    flush();stall=0
    while todo:
        before=len(todo)
        if stall>=3:
            candidates=[]
            for m in todo:
                active=_coords(m,basis,n)
                for b in active:
                    rest=[a for a in active if a!=b];ts=times[b]
                    for a in sorted(rest,key=lambda a:times[a]):ts=max(ts,times[a])+1
                    candidates.append((ts+0.1*len(rest)+rng.random()*0.2,b,rest))
            _,b,rest=min(candidates)
            for a in sorted(rest,key=lambda a:times[a]):cx(a,b);flush()
            stall=0;continue
        candidates=[]
        minimum=min(times)
        for a in range(n):
            for b in range(n):
                if a==b:continue
                nm=basis[a]^basis[b];hit=int(nm in todo)
                la=sum((nm^basis[c]) in todo for c in range(n) if c not in [a,b])
                completion=max(times[a],times[b])+1+hit
                wait=2*max(times[a],times[b])-times[a]-times[b]
                score=gain_weight*hit+look_weight*la-time_weight*(completion-minimum)-0.2*wait+rng.random()*0.5
                candidates.append((score,a,b))
        candidates.sort(reverse=True);used=set();layer=[]
        for score,a,b in candidates:
            if a in used or b in used:continue
            if layer and score<0:continue
            layer.append((a,b));used.update([a,b])
        for a,b in layer:cx(a,b)
        flush();stall=0 if len(todo)<before else stall+1
    q.compose(restore(basis,n),inplace=True)
    return q


def run(record,outdir,seeds):
    assert not outdir.exists();outdir.mkdir(parents=True)
    rec=json.loads(record.read_text());phases=math.pi*np.array([sum(int(m&~w==0) for m in rec['terms']) for w in range(256)],float)
    best=(9999,9999);rows=[]
    for seed in range(seeds):
        q=native(synth(phases,seed));score=(q.depth(),q.count_ops().get('cx',0));row=dict(seed=seed,depth=score[0],cx=score[1]);rows.append(row)
        if score<best:
            best=score;path=outdir/f'kernel_seed{seed}_d{score[0]}.qasm';path.write_text(qasm2.dumps(q))
            op=Operator(qasm2.load(path)).data;want=np.diag(np.exp(1j*phases));phase=np.vdot(want,op);err=float(np.max(abs(op-phase/abs(phase)*want)));assert err<1e-10
            row.update(path=str(path),error=err);print(row,flush=True)
    (outdir/'report.json').write_text(json.dumps(dict(record=str(record),rows=rows),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=100);a=p.parse_args();run(a.record,a.outdir,a.seeds)
