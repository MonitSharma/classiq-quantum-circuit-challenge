"""Phase-parity scheduling with explicitly clean helper wires.

Parities are compared modulo the initial helper variables, which are zero.
The complete invertible linear basis is restored at the end. This promises
only clean-helper columns, never arbitrary helper-input equivalence.
"""
import random
import numpy as np
from qiskit import QuantumCircuit
from depth_parity_network import walsh,restore,_coords


def synth_clean(phases,clean,seed):
    data=(len(phases)-1).bit_length();assert len(phases)==1<<data
    n=data+clean;mask=(1<<data)-1;rng=random.Random(seed);co=walsh(phases)
    todo={m:float(co[m]) for m in range(1,1<<data) if abs(co[m])>1e-12}
    basis=[1<<i for i in range(n)];times=[0]*n;q=QuantumCircuit(n);q.global_phase=float(co[0]);stall=0
    gain=rng.uniform(4,12);look=rng.uniform(.2,2);time=rng.uniform(.2,1.5)
    def flush():
        for b,m in enumerate(basis):
            logical=m&mask
            if logical in todo:q.rz(-2*todo.pop(logical),b);times[b]+=1
    def cx(a,b):
        q.cx(a,b);basis[b]^=basis[a];times[a]=times[b]=max(times[a],times[b])+1
    flush()
    while todo:
        before=len(todo)
        if stall>=3:
            choices=[]
            for m in todo:
                for h in range(1<<clean):
                    active=_coords(m|(h<<data),basis,n)
                    for b in active:
                        rest=[a for a in active if a!=b];finish=times[b]
                        for a in sorted(rest,key=lambda a:times[a]):finish=max(finish,times[a])+1
                        choices.append((finish+.1*len(rest)+rng.random()*.1,b,rest))
            _,b,rest=min(choices)
            for a in sorted(rest,key=lambda a:times[a]):cx(a,b);flush()
            stall=0;continue
        options=[];lowest=min(times)
        for a in range(n):
            for b in range(n):
                if a==b:continue
                nm=(basis[a]^basis[b])&mask;hit=int(nm in todo)
                la=sum((nm^(basis[c]&mask)) in todo for c in range(n) if c not in [a,b])
                completion=max(times[a],times[b])+1+hit
                reward=gain*hit+look*la-time*(completion-lowest)+rng.random()*.5
                options.append((reward,a,b))
        used=set();layer=[]
        for reward,a,b in sorted(options,reverse=True):
            if a in used or b in used:continue
            if layer and reward<0:continue
            layer.append((a,b));used.update([a,b])
        for a,b in layer:cx(a,b)
        flush();stall=0 if len(todo)<before else stall+1
    q.compose(restore(basis,n),inplace=True)
    return q
