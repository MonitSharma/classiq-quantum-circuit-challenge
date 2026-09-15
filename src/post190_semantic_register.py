"""Seeded semantic nine-wire beam scheduler with mutable coordinate registers.

Each register is an exact 64-bit truth table. Seed AND operands must be affine
functions of currently held registers; the target may contain any function.
Affine frames are retained, not undone. A closure test rejects loss of functions
needed to reach the outputs using this seed bank. Search is heuristic, not a
proof of impossibility. Output placement is free.
"""
import argparse,functools,itertools,json,time,random
from pathlib import Path
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
import numpy as np
from distributed_frame_search import native

FULL=(1<<64)-1
INPUTS=tuple(sum(1<<x for x in range(64) if x>>i&1) for i in range(6))

def eval_form(f,signals):
    out=FULL if f[1] else 0
    for i in f[0]:out^=signals[i]
    return out


def bank(w,side):
    signals=list(INPUTS);products=[]
    for g in w['gates']:
        a,b=eval_form(g['a'],signals),eval_form(g['b'],signals)
        products.append((a,b,a&b));signals.append(a&b)
    outs=[eval_form(f,signals) for f in w['outs']]
    assert len(outs)==3
    outs.append(INPUTS[5] if side=='y' else INPUTS[4]^INPUTS[5])
    return tuple(products),tuple(outs)


def pivots(values):
    p={}
    for t in values:
        while t:
            b=t.bit_length()-1
            if b in p:t^=p[b]
            else:p[b]=t;break
    return p


def contains(p,t):
    while t:
        b=t.bit_length()-1
        if b not in p:return False
        t^=p[b]
    return True


def closure(values,products,goals):
    vals=[FULL,*values];p=pivots(vals)
    changed=True
    while changed:
        changed=False
        for a,b,g in products:
            if not contains(p,g) and contains(p,a) and contains(p,b):
                vals.append(g);p=pivots(vals);changed=True
    return all(contains(p,g) for g in goals)


def span_key(values):
    p=pivots([FULL,*values])
    for b in sorted(p):
        for c in p:
            if c>b and p[c]>>b&1:p[c]^=p[b]
    return tuple(p[b] for b in sorted(p,reverse=True))


def remaining_levels(values,products,goals):
    vals=[FULL,*values];p=pivots(vals);levels=[0 if contains(p,g) else None for g in goals]
    for depth in range(1,len(products)+2):
        new=[g for a,b,g in products if not contains(p,g) and contains(p,a) and contains(p,b)]
        if not new:break
        vals+=new;p=pivots(vals)
        for i,g in enumerate(goals):
            if levels[i] is None and contains(p,g):levels[i]=depth
    return sum(v if v is not None else 100 for v in levels)


def expressions(values):
    # Enumerate affine expressions and retain the fewest participating wires.
    result={0:0};seq=[(0,0)]
    for i,v in enumerate([*values,FULL]):
        new=[(t^v,m^(1<<i)) for t,m in seq];seq+=new
        for t,m in new:
            if t not in result or m.bit_count()<result[t].bit_count():result[t]=m
    return result


def step(values,ops):
    out=list(values)
    for kind,ws in ops:
        if kind=='x':out[ws[0]]^=FULL
        elif kind=='cx':out[ws[1]]^=out[ws[0]]
        else:out[ws[2]]^=out[ws[0]]&out[ws[1]]
    return tuple(out)


@functools.lru_cache(None)
def primitive_support():
    q=QuantumCircuit(3);q.rccx(0,1,2);q=native(q)
    return tuple(tuple(q.find_bit(w).index for w in i.qubits) for i in q.data)


def timing(times,ops):
    times=list(times)
    for kind,ws in ops:
        supports=([ws[i] for i in sub] for sub in primitive_support()) if kind=='ccx' else [ws]
        for group in supports:
            group=list(group);t=max(times[w] for w in group)+1
            for w in group:times[w]=t
    return tuple(times)


def expose_pair(a,b,times):
    aa={i for i in range(9) if a>>i&1};bb={i for i in range(9) if b>>i&1}
    if not aa or not bb or aa==bb:return []
    candidates=[]
    for p in aa:
        b2=set(bb);ops=[]
        for c in sorted(aa-{p},key=lambda c:times[c]):
            ops.append(('cx',(c,p)))
            if p in b2:b2.symmetric_difference_update({c})
        for r in b2-{p}:
            tail=[('cx',(c,r)) for c in sorted(b2-{r},key=lambda c:times[c])]
            if a>>9&1:tail.append(('x',(p,)))
            if b>>9&1:tail.append(('x',(r,)))
            pre=ops+tail;nt=timing(times,pre)
            candidates.append((max(nt),len(pre),pre,p,r))
    return sorted(candidates,key=lambda x:x[:2])[:2]


def finish(values,times,goals):
    ops=[];places=[];values=tuple(values)
    for goal in goals:
        if goal in values and values.index(goal) not in places:
            places.append(values.index(goal));continue
        ex=expressions(values)
        if goal not in ex:return None
        mask=ex[goal];candidates=[]
        for target in range(9):
            if target in places or not (mask>>target&1):continue
            tail=[('cx',(j,target)) for j in range(9) if j!=target and mask>>j&1]
            if mask>>9&1:tail.append(('x',(target,)))
            candidates.append((max(timing(times,tail)),tail,target))
        if not candidates:return None
        _,tail,target=min(candidates,key=lambda x:x[0]);values=step(values,tail);times=timing(times,tail);ops+=tail;places.append(target)
    assert len(set(places))==len(goals) and all(values[w]==g for w,g in zip(places,goals))
    return ops,places,times


def compile_ops(ops):
    q=QuantumCircuit(9)
    for kind,ws in ops:
        if kind=='x':q.x(ws[0])
        elif kind=='cx':q.cx(*ws)
        else:q.rccx(*ws)
    return native(q)


def verify(q,places,goals):
    error=0.;phase=None;full=q.copy();full.z(places[0]);full.compose(q.inverse(),inplace=True);full=native(full)
    for x in range(64):
        state=Statevector.from_int(x,512);out=state.evolve(q).data;dest=int(np.argmax(abs(out)))
        assert abs(abs(out[dest])-1)<1e-10
        assert all((dest>>w&1)==(g>>x&1) for w,g in zip(places,goals))
        v=state.evolve(full).data;sign=(-1)**(goals[0]>>x&1)
        if phase is None:phase=v[x]/sign
        want=np.zeros(512,complex);want[x]=phase*sign;error=max(error,float(np.max(abs(v-want))))
    assert error<1e-10
    return dict(depth=q.depth(),cx=q.count_ops().get('cx',0),width=9,outputs=places,checked_inputs=64,inverse_phase_error=error)


def search(w,side,seconds=30,beam=16,steps=24,seed=0,mix=False,audit=None):
    products,goals=bank(w,side);rng=random.Random(seed);start=time.monotonic();expanded=0;rejected=0
    frontier=[(INPUTS+(0,0,0),(0,)*9,[])];seen={};representatives={};best=None;history=[]
    for layer in range(steps):
        candidates=[]
        for values,times,ops in frontier:
            if time.monotonic()-start>seconds:return dict(status='timeout',expanded=expanded,closure_rejections=rejected,history=history),best
            ex=expressions(values)
            if all(g in ex for g in goals):
                done=finish(values,times,goals)
                if done:
                    tail,places,nt=done;q=compile_ops(ops+tail);report=verify(q,places,goals)
                    if best is None or (report['depth'],report['cx'])<(best[0]['depth'],best[0]['cx']):best=(report,q,ops+tail)
                    continue
            for a,b,g in products:
                if a not in ex or b not in ex:continue
                for _,_,pre,p,r in expose_pair(ex[a],ex[b],times):
                    nv=step(values,pre);assert nv[p]==a and nv[r]==b
                    for t,other in itertools.product(range(9),[None,*range(9)] if mix else [None]):
                        if t in (p,r) or (other is not None and other in (p,r,t)):continue
                        tail=pre+([] if other is None else [('cx',(t,other))])+[('ccx',(p,r,t))];out=step(values,tail);nt=timing(times,tail);expanded+=1
                        key=span_key(out);depth=max(nt)
                        if seen.get(key,100000)<=depth:
                            if audit is not None:audit(representatives[key],(out,nt),products,goals)
                            continue
                        if not closure(out,products,goals):rejected+=1;continue
                        seen[key]=depth
                        if audit is not None:representatives[key]=(out,nt)
                        pv=pivots([FULL,*out])
                        have=sum(contains(pv,z) for z in goals)
                        held=sum(contains(pv,z) for _,_,z in products)
                        ready=sum(contains(pv,a) and contains(pv,b) for a,b,_ in products)
                        remaining=remaining_levels(out,products,goals)
                        score=5*have-20*remaining+held+ready*.1-.25*depth+rng.random()*2
                        goal_mask=sum(1<<i for i,g in enumerate(goals) if contains(pv,g))
                        candidates.append((score,out,nt,ops+tail,have,held,goal_mask))
        if not candidates:break
        candidates.sort(key=lambda r:r[0],reverse=True)
        selected=[];per_group={}
        for r in candidates:
            if per_group.get(r[6],0)>=max(2,beam//4):continue
            selected.append(r);per_group[r[6]]=per_group.get(r[6],0)+1
            if len(selected)==beam:break
        frontier=[(r[1],r[2],r[3]) for r in selected]
        row=dict(step=layer+1,available_goals=candidates[0][4],held_seed_products=candidates[0][5],depth=max(candidates[0][2]),expanded=expanded);history.append(row)
        print(side,row,flush=True)
    return dict(status='candidate' if best else 'beam_exhausted_or_step_limit',expanded=expanded,closure_rejections=rejected,history=history),best

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--witness',type=Path,required=True);p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seconds',type=float,default=30);p.add_argument('--beam',type=int,default=16);p.add_argument('--steps',type=int,default=24);p.add_argument('--seed',type=int,default=0);p.add_argument('--mix',action='store_true');a=p.parse_args()
    assert not a.outdir.exists();a.outdir.mkdir(parents=True)
    w=json.loads(a.witness.read_text())
    from post190_degree_rank_bound import targets
    from post190_xag_inplace_lower import outputs
    assert all(outputs(w,x)==[t[x] for t in targets()[a.side]] for x in range(64)), 'witness must match protected code bits'
    r,best=search(w,a.side,a.seconds,a.beam,a.steps,a.seed,a.mix)
    if best:
        text=qasm2.dumps(best[1]);(a.outdir/'encoder.qasm').write_text(text)
        checked=verify(qasm2.loads(text),best[0]['outputs'],bank(w,a.side)[1])
        import hashlib
        checked['sha256']=hashlib.sha256(text.encode()).hexdigest()
        r['best']=checked;r['ops']=best[2]
    (a.outdir/'report.json').write_text(json.dumps(r,indent=2));print({k:v for k,v in r.items() if k not in ('ops','history')},flush=True)
