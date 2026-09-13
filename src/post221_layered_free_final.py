"""Promised-subspace affine/RCCX-layer synthesis, with measured native depth.

Affine matrices are constrained invertible. Only four output wires must
separate classes; the remaining five are arbitrary reversible garbage.
"""
import argparse,json,time
from functools import reduce
from pathlib import Path
import numpy as np
import z3
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from qiskit.synthesis.linear import synth_cnot_count_full_pmh
from distributed_frame_search import native
import two_stage_oracle as ts


def xor(xs):return reduce(lambda a,b:a^b,xs)


def solve(cls,layers,timeout,samples):
    s=z3.Solver();s.set(timeout=timeout);n=len(samples);zero=z3.BitVecVal(0,n)
    regs=[z3.BitVecVal(sum(((v>>b)&1)<<i for i,v in enumerate(samples)),n) for b in range(6)]+[zero]*3
    matrices=[];offsets=[];enabled=[]
    for stage in range(layers+1):
        a=[[z3.Bool(f'a_{stage}_{i}_{j}') for j in range(9)] for i in range(9)]
        inv=[[z3.Bool(f'inv_{stage}_{i}_{j}') for j in range(9)] for i in range(9)]
        off=[z3.Bool(f'offset_{stage}_{i}') for i in range(9)]
        for i in range(9 if stage<layers else 0):
            for j in range(9):s.add(xor([z3.And(a[i][k],inv[k][j]) for k in range(9)])==(i==j))
        new=[z3.BitVec(f'wire_{stage}_{i}',n) for i in range(9)]
        for i in range(9 if stage<layers else 4):s.add(new[i]==(xor([z3.If(a[i][j],regs[j],zero) for j in range(9)])^z3.If(off[i],z3.BitVecVal((1<<n)-1,n),zero)))
        regs=new;matrices.append(a);offsets.append(off)
        if stage<layers:
            en=[z3.Bool(f'en_{stage}_{g}') for g in range(3)];enabled.append(en);regs=regs.copy()
            # Disjoint gates may be permuted and their two controls swapped,
            # absorbing those permutations in the adjacent affine matrices.
            s.add(z3.Implies(en[1],en[0]),z3.Implies(en[2],en[1]))
            for g in range(3):
                forms=[]
                for rr in [3*g,3*g+1]:
                    forms.append(z3.Concat(*[z3.If(b,z3.BitVecVal(1,1),z3.BitVecVal(0,1)) for b in a[rr]+[off[rr]]]))
                s.add(z3.ULE(forms[0],forms[1]))
            for g in range(3):regs[3*g+2]=regs[3*g+2]^z3.If(en[g],regs[3*g]&regs[3*g+1],zero)
    code=[z3.Concat(*[z3.Extract(i,i,regs[b]) for b in reversed(range(4))]) for i in range(n)]
    # The last affine layer can normalize the first encountered affine basis
    # of output codes to 0,1,2,4,8 without changing class separation.
    s.add(code[0]==0)
    for i in range(1,n):
        for bit in range(4):
            threshold=1<<bit
            s.add(z3.Implies(z3.And(*[z3.ULT(c,threshold) for c in code[:i]],z3.UGE(code[i],threshold)),code[i]==threshold))
    for i,v in enumerate(samples):
        for j,u in enumerate(samples[:i]):
            if cls[v]!=cls[u]:s.add(code[i]!=code[j])
    start=time.monotonic();status=s.check();row=dict(layers=layers,status=str(status),samples=samples,symmetry_breaking=True,seconds=time.monotonic()-start)
    if status!=z3.sat:return row,None
    m=s.model();val=lambda b:bool(z3.is_true(m.eval(b,model_completion=True)))
    mats=[[[int(val(b)) for b in rr] for rr in a] for a in matrices];offs=[[int(val(b)) for b in a] for a in offsets];ens=[[val(b) for b in a] for a in enabled]
    # Four independent final rows can always be extended to an invertible map.
    # Eleven distinct classes force rank at least four in the final code.
    from distributed_ucry import rank
    a=mats[-1];rows=[sum(b<<j for j,b in enumerate(rr)) for rr in a[:4]]
    assert rank(rows)==4
    for i in range(9):
        if rank(rows+[1<<i])>len(rows):rows.append(1<<i)
    assert len(rows)==9
    mats[-1]=[[r>>j&1 for j in range(9)] for r in rows];offs[-1][4:]=[0]*5
    states=[]
    for v in range(64):
        rr=[v>>b&1 for b in range(6)]+[0]*3
        for stage,(a,o) in enumerate(zip(mats,offs)):
            rr=[sum(a[i][j]*rr[j] for j in range(9))%2^o[i] for i in range(9)]
            if stage<layers:
                for g in range(3):
                    if ens[stage][g]:rr[3*g+2]^=rr[3*g]&rr[3*g+1]
        states.append(sum(b<<i for i,b in enumerate(rr)))
    assert len(set(states))==64
    bad=[(i,j) for i in range(64) for j in range(i) if cls[i]!=cls[j] and states[i]%16==states[j]%16]
    row.update(matrices=mats,offsets=offs,enabled=ens,states=states,collisions=len(bad))
    return row,bad


def run(outdir,side,layers,timeout,rounds):
    assert not outdir.exists();outdir.mkdir(parents=True);cls=ts.ROWCLS if side=='y' else ts.COLCLS
    samples=list(dict.fromkeys(cls.index(c) for c in cls));records=[]
    for iteration in range(rounds):
        row,bad=solve(cls,layers,timeout,samples);row.update(side=side,iteration=iteration);records.append(row)
        print({k:v for k,v in row.items() if k not in ['matrices','offsets','enabled','states','samples']},flush=True)
        (outdir/'report.json').write_text(json.dumps(records,indent=2)+'\n')
        if bad is None:break
        if bad:
            additions=list(dict.fromkeys(v for pair in bad for v in pair if v not in samples))[:8]
            assert additions;samples=sorted(samples+additions);continue
        q=QuantumCircuit(9);affine_depths=[]
        for stage,(a,off) in enumerate(zip(row['matrices'],row['offsets'])):
            options=[synth_cnot_count_full_pmh(np.array(a,dtype=bool),section_size=s) for s in [1,2,3]]
            aff=min(options,key=lambda q:(q.depth(),q.size()));affine_depths.append(aff.depth());q.compose(aff,inplace=True)
            for i,b in enumerate(off):
                if b:q.x(i)
            if stage<layers:
                for g,on in enumerate(row['enabled'][stage]):
                    if on:q.rccx(3*g,3*g+1,3*g+2)
        q=native(q);path=outdir/f'{side}_encoder_d{q.depth()}.qasm';path.write_text(qasm2.dumps(q));q=qasm2.load(path)
        errors=[]
        for v,w in enumerate(row['states']):
            state=Statevector.from_int(v,512).evolve(q).data;phase=state[w]/abs(state[w]);want=np.zeros(512,complex);want[w]=phase
            errors.append(float(np.max(abs(state-want))))
        assert max(errors)<1e-10
        row.update(path=str(path),native_depth=q.depth(),cx=q.count_ops().get('cx',0),affine_depths=affine_depths,subspace_error=max(errors))
        (outdir/'report.json').write_text(json.dumps(records,indent=2)+'\n');print('verified encoder',q.depth(),max(errors),flush=True);break


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--layers',type=int,default=2);p.add_argument('--timeout-ms',type=int,default=20000);p.add_argument('--rounds',type=int,default=4);a=p.parse_args();run(a.outdir,a.side,a.layers,a.timeout_ms,a.rounds)
