"""Conjugate a diagonal polynomial by exact classical permutations up to phase.

RCCX diagonal garbage cancels in C D C.inverse(), since D is diagonal. No
measurement or initially-zero assumption is used for the reusable kernel.
"""
import argparse,json,math,random
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from distributed_frame_search import native
from post258_kernel_schedule import synth


def transform(poly,controls,target):
    out=poly;cb=sum(1<<c for c in controls)
    for m in range(256):
        if poly>>m&1 and m>>target&1:out^=1<<((m^(1<<target))|cb)
    return out


def terms(poly):return [m for m in range(256) if poly>>m&1]
def values(poly):return np.array([sum(m&~w==0 for m in terms(poly)) for w in range(256)],float)
def cost(poly):return sum([0,0.05,0.5,1,4,12,30,80,200][m.bit_count()] for m in terms(poly))


def run(record,outdir,beam_size,steps):
    assert not outdir.exists();outdir.mkdir(parents=True)
    rec=json.loads(record.read_text());start=sum(1<<m for m in rec['terms']);want=np.diag(np.exp(1j*math.pi*values(start)))
    moves=[((a,),b) for a in range(8) for b in range(8) if a!=b]
    moves += [((a,b),t) for a in range(8) for b in range(a+1,8) for t in range(8) if t not in [a,b]]
    beam=[(cost(start),start,[],[0]*8)];seen={start};candidates=[beam[0]]
    for step in range(steps):
        nxt={}
        for _,poly,hist,times in beam:
            for cs,t in moves:
                p=transform(poly,cs,t)
                if p==poly or p in seen:continue
                dep=times.copy();d=max(dep[w] for w in cs+(t,))+(1 if len(cs)==1 else 9)
                for w in cs+(t,):dep[w]=d
                score=cost(p)+0.8*max(dep)
                if p not in nxt or score<nxt[p][0]:nxt[p]=(score,p,hist+[(cs,t)],dep)
        beam=sorted(nxt.values(),key=lambda r:r[0])[:beam_size];seen.update(r[1] for r in beam);candidates.extend(beam[:5])
        print('step',step+1,'best',[round(beam[0][0],2),cost(beam[0][1]),max(beam[0][3])],flush=True)
    # Compile a bounded diverse shortlist; estimated polynomial cost is not depth.
    best=(9999,9999);results=[]
    for idx,(_,poly,hist,times) in enumerate(sorted(candidates,key=lambda r:r[0])[:16]):
        change=QuantumCircuit(8)
        for cs,t in hist:
            if len(cs)==1:change.cx(cs[0],t)
            else:change.rccx(cs[0],cs[1],t)
        # Successive substitutions build f(P1(P2(...x))). Reverse physical
        # chronological order in C makes C.inverse() D C recover f.
        # We test both orientation conventions symbolically below.
        angles=math.pi*values(poly)
        cores=[native(synth(angles,seed)) for seed in [0,3,11,21,28,91]]
        core=min(cores,key=lambda q:(q.depth(),q.size()))
        q=change.copy();q.compose(core,inplace=True);q.compose(change.inverse(),inplace=True);q=native(q)
        op=Operator(q).data;phase=np.vdot(want,op);err=float(np.max(abs(op-phase/abs(phase)*want)))
        if err>1e-10:
            reverse=QuantumCircuit(8)
            for cs,t in reversed(hist):
                if len(cs)==1:reverse.cx(cs[0],t)
                else:reverse.rccx(cs[0],cs[1],t)
            q=reverse.copy();q.compose(core,inplace=True);q.compose(reverse.inverse(),inplace=True);q=native(q)
            op=Operator(q).data;phase=np.vdot(want,op);err=float(np.max(abs(op-phase/abs(phase)*want)))
        assert err<1e-10,err
        score=(q.depth(),q.count_ops().get('cx',0));r=dict(index=idx,depth=score[0],cx=score[1],history=hist,polynomial=terms(poly),core_depth=core.depth(),error=err);results.append(r)
        if score<best:
            best=score;path=outdir/f'kernel{idx}_d{score[0]}.qasm';path.write_text(qasm2.dumps(q));r['path']=str(path);print('kernel',score,flush=True)
    (outdir/'report.json').write_text(json.dumps(dict(record=str(record),beam_size=beam_size,steps=steps,results=results),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--beam',type=int,default=30);p.add_argument('--steps',type=int,default=5);a=p.parse_args();run(a.record,a.outdir,a.beam,a.steps)
