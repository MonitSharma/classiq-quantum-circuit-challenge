"""Compile new class descriptors into a fresh diagonal kernel and full oracle.

Actual encoder basis outputs determine the care set. Coordinates can contain
reversible garbage; C / diagonal / C.inverse restores them and cancels phases.
The protected permuted kernel is deliberately not reused with new labels.
"""
import argparse,json,math,hashlib
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector,Operator
from two_stage_oracle import ROWCLS,COLCLS,logo
from build_two_stage_196 import encoders,KERNEL_WIRES
from post190_register_compose import WIRES
from post190_nonlinear_care import solve_phase
from post218_beam_phase import psynth
from distributed_frame_search import native


def descriptor(q,side):
    assert q.num_qubits==9 and set(q.count_ops()) <= {'u3','cx'}
    raw=5 if side=='y' else 4
    codes=[]
    for x in range(64):
        state=Statevector.from_int(x,512).evolve(q).data
        dest=int(np.argmax(abs(state)))
        assert abs(abs(state[dest])-1)<1e-10
        codes.append(((dest>>raw)&1)|(((dest>>6)&7)<<1))
    classes=ROWCLS if side=='y' else COLCLS
    assigned={}
    for x,c in enumerate(codes):
        if c in assigned:assert assigned[c]==classes[x], 'descriptor merges distinct classes'
        assigned[c]=classes[x]
    return codes


def care_set(xcodes,ycodes):
    values={}
    for x in range(64):
        for y in range(64):
            word=ycodes[y]|(xcodes[x]<<4);v=int(logo(x,y))
            if word in values:assert values[word]==v,'descriptor collision changes oracle phase'
            values[word]=v
    care=np.array(sorted(values),dtype=int)
    return care,np.array([values[w] for w in care],float)


def compose(replacements,seed=190):
    codes=json.loads(Path('artifacts/190/class_codes.json').read_text())
    base=encoders(codes,298,506);parts={}
    for side,ws in WIRES.items():
        if side in replacements:parts[side]=replacements[side]
        else:
            q=QuantumCircuit(9);index={v:i for i,v in enumerate(ws)}
            for inst in base.data:
                wires=[base.find_bit(v).index for v in inst.qubits]
                if set(wires)<=set(ws):q.append(inst.operation,[index[w] for w in wires])
            parts[side]=q
    descriptors={s:descriptor(q,s) for s,q in parts.items()}
    care,truth=care_set(descriptors['x'],descriptors['y'])
    had=np.array([[1-2*((int(w)&m).bit_count()%2) for m in range(256)] for w in care],float)
    support,co=solve_phase(had,truth,np.random.default_rng(seed),4)
    kernel=psynth(8,{m:float(math.pi*co[m]) for m in range(1,256) if abs(co[m])>1e-9},global_phase=float(math.pi*co[0]),seed=seed,beam=32,branch=12,alpha=6.,timew=1.4,horizon=1.5,fill=2)
    kernel=native(kernel)
    actual=Operator(kernel).data[:,care];expected=np.zeros_like(actual)
    expected[care,np.arange(len(care))]=np.exp(1j*math.pi*truth)
    phase=np.vdot(expected,actual);phase/=abs(phase)
    error=float(np.max(abs(actual-phase*expected)));assert error<1e-8
    e=QuantumCircuit(18)
    for side,q in parts.items():e.compose(q,WIRES[side],inplace=True)
    full=native(e.compose(kernel,KERNEL_WIRES).compose(e.inverse()))
    return full,dict(descriptors=descriptors,care_words=len(care),phase_terms=support,kernel_depth=kernel.depth(),kernel_error=error,depth=full.depth(),cx=full.count_ops().get('cx',0),width=18)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--x',type=Path);p.add_argument('--y',type=Path);p.add_argument('--outdir',required=True,type=Path);a=p.parse_args()
    assert not a.outdir.exists();a.outdir.mkdir(parents=True)
    full,report=compose({s:qasm2.load(v) for s,v in [('x',a.x),('y',a.y)] if v})
    text=qasm2.dumps(full);path=a.outdir/'oracle.qasm';path.write_text(text)
    from exhaustive_verify import exhaustive
    exhaustive(path)
    report['sha256']=hashlib.sha256(text.encode()).hexdigest()
    (a.outdir/'report.json').write_text(json.dumps(report,indent=2));print(report)
