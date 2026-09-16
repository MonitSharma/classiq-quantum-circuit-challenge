"""Complete phase-root schedule control with paid, retained affine frames.

Uses existing six-slot witnesses, not a new pebbling search campaign. This
control preserves affine access to all input coordinates; it is less general
than PhaseRooted's destructive search. Physical coordinate wires may be targets.
Relative-phase ANDs are only inserted into zero targets and removed from pure
product targets, so matching compute/release phases cancel even across frames.
"""
from __future__ import annotations
import argparse, json, math, random
from pathlib import Path
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import U3Gate
from destructive_phase_xag import clock_ops, apply
from destructive_xag import load_xag
from distributed_frame_search import native
from direct_e_v2 import margolus
from md_xag import mask_indices, xor_mask, input_truth_tables, FULL


def coefficients(rows, value):
    piv={0:(1,1<<len(rows))}
    for w,v in enumerate(rows):
        c=1<<w
        while v:
            k=v.bit_length()-1
            if k in piv:a,b=piv[k];v^=a;c^=b
            else:piv[k]=(v,c);break
    c=0
    while value:
        k=value.bit_length()-1
        if k not in piv:return None
        a,b=piv[k];value^=a;c^=b
    return c


def affine(rows, ops):
    rows=list(rows)
    for name,ws in ops:
        if name=='cx':rows[ws[1]]^=rows[ws[0]]
        elif name=='x':rows[ws[0]]^=1
        else:raise ValueError(name)
    return tuple(rows)


def expose(rows,left,right,clocks,limit=3):
    a,b=coefficients(rows,left),coefficients(rows,right)
    assert a is not None and b is not None
    n=len(rows);low=(1<<n)-1;out=[]
    for p in mask_indices(a&low):
        first=[('cx',[c,p]) for c in mask_indices(a&low) if c!=p]
        second=b&low
        if second>>p&1:second^=(a&low)^(1<<p)
        for r in mask_indices(second&~(1<<p)):
            ops=first+[('cx',[c,r]) for c in mask_indices(second) if c!=r]
            if a>>n&1:ops.append(('x',[p]))
            if b>>n&1:ops.append(('x',[r]))
            framed=affine(rows,ops);assert framed[p]==left and framed[r]==right
            times=clock_ops(clocks,ops)
            out.append((max(times),len(ops),ops,p,r,framed,times))
    out.sort(key=lambda x:x[:2]);return out[:limit]


def root_witnesses(parsed):
    from xag import plan
    from xag_to_inplace_layers import XAGGraph
    graph=XAGGraph(parsed.nodes)
    return {r:plan(graph,frozenset(),graph.nodes[r],limit=6,max_states=60000)
            for r in mask_indices(parsed.output_affine_mask) if r>=13}


def build(parsed,witnesses,seed=0):
    rng=random.Random(seed);rows=tuple(1<<(i+1) for i in range(12))+(0,)*6
    clocks=(0,)*18;ops=[];live=set();history=[]
    roots=list(witnesses);rng.shuffle(roots)
    def add(block):
        nonlocal clocks
        ops.extend(block);clocks=clock_ops(clocks,block)
    for s in mask_indices(parsed.output_affine_mask):
        if 1<=s<=12:add([('z',[s-1])])
    def toggle(v):
        nonlocal rows
        node=parsed.nodes[v-13];release=v in live;choices=[]
        for _,_,pre,a,b,framed,times in expose(rows,node.left_affine_mask,node.right_affine_mask,clocks):
            for t in range(18):
                if t in (a,b):continue
                if release:
                    coeff=coefficients(framed,1<<v)
                    if coeff is None or not coeff>>t&1:continue
                    fix=[('cx',[w,t]) for w in mask_indices(coeff&((1<<18)-1)) if w!=t]
                    if coeff>>18&1:fix.append(('x',[t]))
                    third=affine(framed,fix);assert third[t]==1<<v
                    # Remove this logical product from every other register.
                    fix += [('cx',[t,w]) for w in range(18) if w!=t and third[w]>>v&1]
                else:
                    others=list(framed);others[t]=0
                    coeff=coefficients(others,framed[t])
                    if coeff is None:continue
                    fix=[('cx',[w,t]) for w in mask_indices(coeff&((1<<18)-1))]
                    if coeff>>18&1:fix.append(('x',[t]))
                final=affine(framed,fix)
                assert final[a]==node.left_affine_mask and final[b]==node.right_affine_mask
                assert final[t]==(1<<v if release else 0)
                final=list(final);final[t]^=1<<v
                block=pre+fix+[('ccx',[a,b,t])];end=clock_ops(clocks,block)
                choices.append(((max(end),sum(end),rng.random()),tuple(final),block,t))
        assert choices,('no physical lowering',v,release,live)
        _,rows,block,t=min(choices,key=lambda c:c[0]);add(block)
        history.append(dict(node=v,release=release,target=t))
        if release:live.remove(v)
        else:live.add(v)
    for root in roots:
        sequence=witnesses[root]
        for v in sequence:toggle(v)
        node=parsed.nodes[root-13]
        _,_,pre,a,b,rows,_=expose(rows,node.left_affine_mask,node.right_affine_mask,clocks,1)[0]
        add(pre+[('cz',[a,b])])
        for v in reversed(sequence):toggle(v)
        assert not live
    # Restore the remaining affine coordinate frame, paying every operation.
    for i in range(12):
        j=next(j for j in range(i,18) if rows[j]>>(i+1)&1)
        block=[]
        if j!=i:block=[('cx',[i,j]),('cx',[j,i]),('cx',[i,j])]
        rows=affine(rows,block);add(block)
        block=[('cx',[i,j]) for j in range(18) if j!=i and rows[j]>>(i+1)&1]
        rows=affine(rows,block);add(block)
    block=[('x',[i]) for i in range(18) if rows[i]&1];rows=affine(rows,block);add(block)
    assert rows==tuple(1<<(i+1) for i in range(12))+(0,)*6
    # Independent all-4096-bit Boolean replay including phase and restoration.
    actual=tuple(input_truth_tables())+(0,)*6;initial=actual;phase=0
    for name,ws in ops:
        if name=='z':phase^=actual[ws[0]]
        elif name=='cz':phase^=actual[ws[0]]&actual[ws[1]]
        else:actual=apply(actual,[(name,ws)])
    assert actual==initial and phase^parsed.graph.evaluate() in (0,FULL)
    return ops,dict(seed=seed,depth=max(clocks),cx=sum(n=='cx' for n,_ in ops)+3*len(history)+len(roots),
                   toggles=len(history),coordinate_and_targets=sum(h['target']<12 for h in history),roots=roots)


def emit_paired(ops):
    q=QuantumCircuit(18);primitive=margolus()
    # The real Margolus primitive is self-adjoint. Each logical AND creation
    # from zero is paired with removal from that same function, so relative
    # phases cancel. Exhaustive serialized-QASM verification remains mandatory.
    for name,ws in ops:
        if name=='ccx':q.compose(primitive,ws,inplace=True)
        elif name=='cx':q.cx(*ws)
        elif name=='x':q.append(U3Gate(math.pi,0,math.pi),ws)
        elif name=='z':q.append(U3Gate(0,0,math.pi),ws)
        elif name=='cz':
            q.append(U3Gate(math.pi/2,0,math.pi),[ws[1]]);q.cx(*ws)
            q.append(U3Gate(math.pi/2,0,math.pi),[ws[1]])
    return q


def campaign(out,trials=100):
    assert not out.exists();out.mkdir(parents=True)
    parsed=load_xag(Path('artifacts/multiplicative_depth/optimized/advanced_round4.xag'))
    witnesses=root_witnesses(parsed);(out/'witnesses.json').write_text(json.dumps(witnesses,indent=2)+'\n')
    results=[];best=None
    for seed in range(trials):
        ops,r=build(parsed,witnesses,seed);results.append(r)
        if best is None or r['depth']<best['depth']:
            best=r;print(r,flush=True)
            (out/'best.json').write_text(json.dumps(dict(**r,ops=ops),indent=2)+'\n')
        (out/'report.json').write_text(json.dumps(results,indent=2)+'\n')
    best=json.loads((out/'best.json').read_text());raw=emit_paired(best['ops'])
    assert raw.depth()==best['depth']
    q=min([raw,native(raw)],key=lambda q:q.depth());path=out/'oracle.qasm';path.write_text(qasm2.dumps(q))
    from exhaustive_verify import exhaustive
    exhaustive(path)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--trials',type=int,default=100);a=p.parse_args();campaign(a.outdir,a.trials)
