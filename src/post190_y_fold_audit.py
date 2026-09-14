"""Audit the measured y fold and a disk-only y5-band alternative.

These are verified arithmetic components, not improved full-logo oracles.
"""
import json,hashlib,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from distributed_frame_search import native
from post190_y_fold import build,check,simulate,add_const


def disk_fold():
    q=QuantumCircuit(9)
    add_const(q,13,helpers=[6,7,8])
    add_const(q,10,control=5,helpers=[6,7,8])
    for i in range(4):q.cx(4,i)
    return q


def quantum_check(raw):
    q=native(raw);full=q.copy();full.z(0);full.compose(q.inverse(),inplace=True);full=native(full)
    phase=None;error=0.
    for y in range(64):
        dest=simulate(raw,y)
        v=Statevector.from_int(y,1<<q.num_qubits).evolve(q).data
        assert abs(abs(v[dest])-1)<1e-10
        v=Statevector.from_int(y,1<<q.num_qubits).evolve(full).data
        sign=(-1)**(dest&1)
        if phase is None:phase=v[y]/sign
        expected=np.zeros_like(v);expected[y]=phase*sign
        error=max(error,float(np.max(abs(v-expected))))
    assert error<1e-10
    return q,dict(depth=q.depth(),cx=q.count_ops().get('cx',0),width=q.num_qubits,checked_inputs=64,phase_inverse_error=error)


def audit(out):
    assert not out.exists();out.mkdir(parents=True)
    original=build();oq,old=quantum_check(original);old['collisions']=check(original)
    raw=disk_fold();q,new=quantum_check(raw)
    for y in range(64):
        word=simulate(raw,y);assert word>>6==0
        assert ((word>>5)&1)==y>>5
        b=y>>5;d=((y&31)-(19 if b==0 else 9))%32
        assert ((word>>4)&1)==d>>4
        assert word&15==(d&15)^(15 if d>>4 else 0)
        absdy=(word&15)+((word>>4)&1)
        for x in range(64):
            actual=((x-40)**2+(y-19)**2<=72) or ((x-55)**2+(y-41)**2<=42)
            folded=(x-(40 if b==0 else 55))**2+absdy**2 <= (72 if b==0 else 42)
            assert actual==folded,(x,y)
    new['disk_predicate_pairs_checked']=4096
    # A useful alternative radius code when looking up radius from |dx|.
    radius={str(R):[math.isqrt(R-d*d) for d in range(math.isqrt(R)+1)] for R in (72,42)}
    values=sorted({r for rs in radius.values() for r in rs})
    assert values==[2,4,5,6,7,8]
    shifted=[r-1 for r in values];assert min(shifted)>0 and max(shifted)<=7
    for name,circ in [('original',oq),('disk_y5',q)]:
        (out/(name+'.qasm')).write_text(qasm2.dumps(circ))
    report=dict(original=old,disk_y5=new,square_interval_cardinality=25,raw_descriptor_widths={'band_mag':5,'band_sign_mag':6,'band_sign_mag_y5':7},radii_from_abs_dx=radius,radius_minus_one_codes=shifted,empty_radius_code=0,protected_sha256=hashlib.sha256(Path('artifacts/190/two_stage_190.qasm').read_bytes()).hexdigest())
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();audit(a.outdir)
