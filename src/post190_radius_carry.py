"""Original-y interval phase via two carry comparisons and shifted radius.

Radius t occupies 12:15; 15,16 are threshold extension bits; 17 is the
x5 AND (t!=0) enable. y5 doubles as a known initial carry inside each
comparison and is restored by its inverse. No y-fold is computed.
"""
import functools,json
from pathlib import Path
from qiskit import QuantumCircuit,qasm2
from qiskit.synthesis import synth_mcx_noaux_v24
from distributed_frame_search import native
from post190_y_fold import mcx
from post190_radius_interval import make_lookup,rectangle_phase

@functools.lru_cache(None)
def many_x(n):
    q=QuantumCircuit(n+1)
    if n==1:q.cx(0,1)
    elif n==2:q.ccx(0,1,2)
    else:q.compose(synth_mcx_noaux_v24(n),inplace=True)
    return native(q)


def add(q,amount,wires,control=None):
    for k in range(4,-1,-1):
        if not (amount>>k)&1:continue
        for j in range(4,k,-1):
            controls=wires[k:j]+([] if control is None else [control])
            q.compose(many_x(len(controls)),controls+[wires[j]],inplace=True)
        if control is None:q.x(wires[k])
        else:q.cx(control,wires[k])


def interval_phase():
    a=list(range(12,17));flag=17
    valid=QuantumCircuit(18);valid.cx(5,flag);valid.x([12,13,14])
    mcx(valid,[5,12,13,14],flag,[15,16]);valid.x([12,13,14])
    q=valid.copy()
    for upper in [True,False]:
        prep=QuantumCircuit(18)
        if upper:add(prep,21,a)
        else:prep.x(a);add(prep,19,a) # 31-t+19 mod32 = 18-t
        add(prep,21,a,control=11) # -11*y5 mod32
        comp=QuantumCircuit(18);comp.x(list(range(6,11)));carry=11
        for i in range(5):
            comp.cx(a[i],6+i);comp.cx(a[i],carry);comp.rccx(6+i,carry,a[i]);carry=a[i]
        q.compose(prep,inplace=True);q.compose(comp,inplace=True);q.cz(a[4],flag)
        q.compose(comp.inverse(),inplace=True);q.compose(prep.inverse(),inplace=True)
    q.compose(valid.inverse(),inplace=True)
    return native(q)


def run(out):
    assert not out.exists();out.mkdir(parents=True)
    lookup,values,lr=make_lookup()
    e=QuantumCircuit(18)
    for i in range(5):e.cx(11,i)
    e.x(3);e.cx(3,4)
    for i in range(4):e.cx(4,i)
    e.compose(lookup,[0,1,2,3,4,11,12,13,14],inplace=True);e=native(e)
    k=interval_phase();print('carry interval',k.depth(),k.count_ops(),flush=True)
    rect,_=rectangle_phase();disk=native(e.compose(k).compose(e.inverse()));full=native(rect.compose(disk))
    for name,q in [('interval',k),('disk',disk),('oracle',full)]:
        (out/(name+'.qasm')).write_text(qasm2.dumps(q))
    from exhaustive_verify import exhaustive
    exhaustive(out/'oracle.qasm')
    r=dict(lookup=lr,encoder_depth=e.depth(),interval_depth=k.depth(),interval_cx=k.count_ops().get('cx',0),disk_depth=disk.depth(),depth=full.depth(),cx=full.count_ops().get('cx',0),width=18)
    (out/'report.json').write_text(json.dumps(r,indent=2));print(r,flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--outdir',required=True,type=Path);a=p.parse_args();run(a.outdir)
