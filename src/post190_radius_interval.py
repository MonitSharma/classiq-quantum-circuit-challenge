"""Concrete radius-from-folded-x oracle with original-y interval phases.

This first construction uses disjoint dyadic interval phases as an explicit
baseline. It measures the whole job, rather than pricing an unbuilt comparator.
"""
import argparse,functools,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from qiskit.synthesis import synth_mcx_2_clean_kg24
from distributed_frame_search import native
from post224_relative_lookup import relative
from two_stage_oracle import logo


def dyadic(lo,hi):
    out=[]
    while lo<=hi:
        size=(lo & -lo) if lo else 1<<(hi+1).bit_length()-1
        while size>hi-lo+1:size//=2
        out.append((lo,size));lo+=size
    return out


def literals(lo,size,wires):
    return [(w,(lo>>i)&1) for i,w in enumerate(wires) if (1<<i)>=size]


@functools.lru_cache(None)
def positive_phase(n):
    if n<=3:
        q=QuantumCircuit(n)
        if n==1:q.z(0)
        elif n==2:q.cz(0,1)
        else:q.ccz(0,1,2)
    else:
        q=QuantumCircuit(n+2);q.h(n-1)
        q.compose(synth_mcx_2_clean_kg24(n-1),inplace=True);q.h(n-1)
    return native(q)


def emit_cube(q,ls,helpers=(15,16)):
    assert len({w for w,_ in ls})==len(ls)
    ws=[w for w,_ in ls];neg=[w for w,b in ls if not b]
    assert not set(ws)&set(helpers)
    if neg:q.x(neg)
    sub=positive_phase(len(ws));q.compose(sub,ws+list(helpers) if sub.num_qubits>len(ws) else ws,inplace=True)
    if neg:q.x(neg)


def rectangle_phase():
    q=QuantumCircuit(18);count=0
    for xl,xh,yl,yh in [(2,26,29,53),(27,48,39,43)]:
        for x,sx in dyadic(xl,xh):
            for y,sy in dyadic(yl,yh):
                emit_cube(q,literals(x,sx,list(range(6)))+literals(y,sy,list(range(6,12))));count+=1
    return native(q),count


def interval_phase():
    q=QuantumCircuit(18);count=0
    for b in (0,1):
        c=19 if b==0 else 9
        for t in (1,3,4,5,6,7):
            if b==1 and t>5:continue # unreachable for the smaller disk
            fixed=[(5,1),(11,b)]+[(12+j,(t>>j)&1) for j in range(3)]
            for v,size in dyadic(c-t-1,c+t+1):
                emit_cube(q,fixed+literals(v,size,list(range(6,11))));count+=1
    return native(q),count


def folded(a):
    x=a&63;b=a>>6;v=x^(31 if b else 0);d=((v&31)-8)%32
    return (d&15)^(15 if d>>4 else 0),(d>>4)


def make_lookup(seeds=48):
    vals=[]
    for a in range(64):
        d=(a&15)+((a>>4)&1);R=42 if a>>5 else 72
        vals.append(math.isqrt(R-d*d)-1 if d*d<=R else 0)
    table=np.array([[math.pi*(v>>j&1) for v in vals] for j in range(3)])
    best=None
    for seed in range(seeds):
        q,_=relative(table,seed);score=(q.depth(),q.count_ops().get('cx',0))
        if best is None or score<best[0]:best=(score,q,seed)
    q=best[1];error=0.
    for a in range(64):
        v=Statevector.from_int(a,512).evolve(q).data;dest=a|(vals[a]<<6)
        error=max(error,float(abs(abs(v[dest])-1)))
    assert error<1e-10
    return q,vals,dict(depth=q.depth(),cx=best[0][1],seed=best[2],basis_inputs_checked=64,magnitude_error=error)


def build(out):
    assert not out.exists();out.mkdir(parents=True)
    lookup,values,lr=make_lookup()
    fold=QuantumCircuit(18)
    for i in range(5):fold.cx(11,i)
    fold.x(3);fold.cx(3,4)
    for i in range(4):fold.cx(4,i)
    e=fold.copy();e.compose(lookup,[0,1,2,3,4,11,12,13,14],inplace=True);e=native(e)
    # Independent classical composition includes x high enable and disjoint bridge.
    for x in range(64):
        for y in range(64):
            b=y>>5;m,s=folded(x|(b<<6));t=values[m|(s<<4)|(b<<5)];c=19 if not b else 9
            disk=bool(x&32) and t!=0 and c-t-1 <= (y&31) <= c+t+1
            rect=(2<=x<=26 and 29<=y<=53) or (27<=x<=48 and 39<=y<=43)
            assert not (disk and rect)
            assert bool(disk^rect)==logo(x,y),(x,y)
    k,kc=interval_phase();print('interval',k.depth(),k.count_ops(),flush=True)
    rect,rc=rectangle_phase();print('rectangles',rect.depth(),rect.count_ops(),flush=True)
    disk=native(e.compose(k).compose(e.inverse()))
    full=native(rect.compose(disk))
    report=dict(radius_lookup=lr,fold_depth=native(fold).depth(),fold_plus_lookup_depth=e.depth(),interval_depth=k.depth(),interval_cx=k.count_ops().get('cx',0),interval_cubes=kc,rectangle_depth=rect.depth(),rectangle_cubes=rc,disk_depth=disk.depth(),depth=full.depth(),cx=full.count_ops().get('cx',0),width=18,truth_pairs_checked=4096)
    for name,q in [('radius_lookup',lookup),('interval',k),('rectangles',rect),('oracle',full)]:
        (out/(name+'.qasm')).write_text(qasm2.dumps(q))
    from exhaustive_verify import exhaustive
    exhaustive(out/'oracle.qasm')
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();build(a.outdir)
