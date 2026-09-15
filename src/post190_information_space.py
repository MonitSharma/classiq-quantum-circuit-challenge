"""Bounded exact-truth register search; failure is never an UNSAT certificate.

Full truth tables describe all 512 inputs, while goals constrain only the first
64. Semantic transitions select affine control/target bases; physical routing
is synthesized separately. Beam and exposure caps are explicitly heuristic.
"""
import argparse,functools,itertools,json,time,random,hashlib
from dataclasses import dataclass
from pathlib import Path
from qiskit import qasm2
import post190_semantic_register as s

ALL=(1<<512)-1

def full_truth_var(i):
    assert 0<=i<9
    return sum(1<<x for x in range(512) if x>>i&1)

INITIAL=tuple(full_truth_var(i) for i in range(9))

def restrict_clean(t):return t&s.FULL

@functools.lru_cache(4096)
def affine_span(values):
    """Full function -> coefficient mask (bit9 is the constant)."""
    result={0:0}
    for i,v in enumerate((*values,ALL)):
        result.update({t^v:m^(1<<i) for t,m in tuple(result.items())})
    return result

@functools.lru_cache(4096)
def preimage_bank(values):
    out={}
    for t,m in affine_span(values).items():out.setdefault(restrict_clean(t),[]).append((t,m))
    return out

def affine_preimages_of_clean_function(values,goal):return tuple(preimage_bank(tuple(values)).get(goal,()))

def full_step(values,ops):
    out=list(values)
    for kind,ws in ops:
        if kind=='x':out[ws[0]]^=ALL
        elif kind=='cx':out[ws[1]]^=out[ws[0]]
        else:out[ws[2]]^=out[ws[0]]&out[ws[1]]
    return tuple(out)

def evaluate_mask(values,m):
    out=ALL if m>>9&1 else 0
    for i,v in enumerate(values):
        if m>>i&1:out^=v
    return out

@functools.lru_cache(8192)
def frame_ops(masks):
    """Gaussian elimination, reversed to synthesize the requested row matrix."""
    rows=[m&511 for m in masks];reduce=[]
    for col in range(9):
        pivot=next((j for j in range(col,9) if rows[j]>>col&1),None)
        if pivot is None:raise ValueError('singular affine frame')
        if pivot!=col:
            for c,t in [(pivot,col),(col,pivot),(pivot,col)]:rows[t]^=rows[c];reduce.append(('cx',(c,t)))
        for j in range(9):
            if j!=col and rows[j]>>col&1:rows[j]^=rows[col];reduce.append(('cx',(col,j)))
    assert rows==[1<<i for i in range(9)]
    return tuple(reversed(reduce))+tuple(('x',(i,)) for i,m in enumerate(masks) if m>>9&1)

def synthesize_affine_frame(old_basis,new_basis):
    ex=affine_span(tuple(old_basis));masks=tuple(ex[t] for t in new_basis)
    ops=frame_ops(masks);assert full_step(old_basis,ops)==tuple(new_basis)
    q=s.compile_ops(ops)
    return q,q.depth(),q.count_ops().get('cx',0)

def canonical(values,constant):
    p=s.pivots((constant,*values))
    for b in sorted(p):
        for c in p:
            if c>b and p[c]>>b&1:p[c]^=p[b]
    return tuple(p[b] for b in sorted(p,reverse=True))

@functools.lru_cache(16384)
def _state_metrics(clean,products,goals):
    p=s.pivots((s.FULL,*clean));rank=len(p)
    present=tuple(i for i,g in enumerate(goals) if s.contains(p,g))
    held=tuple(i for i,(_,_,g) in enumerate(products) if s.contains(p,g))
    ready=tuple(i for i,(a,b,g) in enumerate(products) if s.contains(p,a) and s.contains(p,b) and not s.contains(p,g))
    deficit=len(s.pivots((s.FULL,*clean,*goals)))-rank
    return dict(present=list(present),missing=[i for i in range(len(goals)) if i not in present],rank_deficit=deficit,held=list(held),ready=list(ready),clean_rank=rank,remaining=s.remaining_levels(clean,products,goals),inputs=sum(s.contains(p,x) for x in s.INPUTS))

def state_metrics(clean,products,goals):
    return _state_metrics(canonical(clean,s.FULL),products,goals)

@functools.lru_cache(16384)
def semantic_closure(clean_basis,products,goals):
    return s.closure(clean_basis,products,goals)

@dataclass
class State:
    values:tuple
    times:tuple
    ops:tuple
    stages:int=0
    @property
    def clean(self):return tuple(map(restrict_clean,self.values))

class Dominance:
    """Only componentwise timing dominance on IDENTICAL ordered wire functions.

Cross-basis representatives are never called dominated. Beam truncation is
separate, and is an acknowledged incomplete heuristic.
"""
    def __init__(self,mode):self.mode=mode;self.seen={};self.spans=set();self.accepted=0
    def accept(self,state):
        span=canonical(state.clean,s.FULL);self.spans.add(span)
        if self.mode=='span':
            old=self.seen.get(span,10**9)
            if old<=max(state.times):return False
            self.seen[span]=max(state.times)
        elif self.mode=='physical':
            key=(state.values,state.times)
            if key in self.seen:return False
            self.seen[key]=True
        else:
            key=state.values;old=self.seen.get(key,[])
            if any(all(a<=b for a,b in zip(t,state.times)) for t in old):return False
            self.seen[key]=[t for t in old if not all(a<=b for a,b in zip(state.times,t))]+[state.times]
        self.accepted+=1;return True

def broad_expose(a,b,times,limit):
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
            pre=tuple(ops+tail);candidates.append((max(s.timing(times,pre)),len(pre),pre,p,r))
    return sorted(candidates,key=lambda v:v[:2])[:limit]

def desired_frame(a,b,preferred,rng):
    """Choose independent control rows, then a goal/operand-aware completion.

Random XORs of the target row into completion rows change the information
retained by a destructive target update; they are not treated as free gates.
"""
    rows=[a,b];basis=s.pivots((a&511,b&511))
    if len(basis)!=2:return None
    for m in preferred+[1<<i for i in rng.sample(range(9),9)]:
        if not s.contains(basis,m&511):
            rows.append(m);basis=s.pivots(tuple(r&511 for r in rows))
            if len(rows)==9:break
    if len(rows)!=9:return None
    for j in range(3,9):
        if rng.randrange(2):rows[j]^=rows[2]
    return tuple(rows)

def exposures(state,a,b,goals,mode,aliases,limit,rng):
    bank=preimage_bank(state.values)
    if a not in bank or b not in bank:return
    # Preserve alternative physical masks, including equal-clean extensions.
    key=lambda tm:((tm[1]&511).bit_count(),sum(state.times[i] for i in range(9) if tm[1]>>i&1),tm[1])
    av=sorted(bank[a],key=key)[:aliases];bv=sorted(bank[b],key=key)[:aliases]
    candidates=[];seen=set()
    for (_,am),(_,bm) in itertools.product(av,bv):
        for cost,n,pre,p,r in broad_expose(am,bm,state.times,limit):
            sig=(pre,p,r)
            if sig not in seen:candidates.append((cost,pre,p,r));seen.add(sig)
    candidates.sort(key=lambda row:row[0])
    for _,pre,p,r in candidates[:limit]:yield pre,p,r
    if mode=='information':
        preferred=[m for g in goals for _,m in bank.get(g,[])[:1]]
        for (_,am),(_,bm) in list(itertools.product(av,bv))[:limit]:
            rows=desired_frame(am,bm,preferred,rng)
            if rows:
                pre=frame_ops(rows)
                yield pre,0,1

def pack_options(values,first,products,maximum):
    """After the common frame, enumerate disjoint RCCXs already exposed.

All controls are read from the pre-stage basis; supports are disjoint.
This is bounded packing, not exhaustive simultaneous affine-frame synthesis.
"""
    out=[tuple(first)];used=set(w for _,ws in first for w in ws)
    if maximum==1:return out
    clean=tuple(map(restrict_clean,values));options=[]
    for a,b,g in products:
        for p in range(9):
            if p in used or clean[p]!=a:continue
            for r in range(9):
                if r in used or r==p or clean[r]!=b:continue
                for t in range(9):
                    if t not in used and t not in (p,r) and clean[t]!=(clean[p]&clean[r]):options.append(('ccx',(p,r,t)))
    for op in options[:24]:
        out.append((*first,op))
        if maximum>=3:
            busy=used|set(op[1])
            for op2 in options:
                if not busy.intersection(op2[1]):out.append((*first,op,op2));break
    return out

def nonlinear_depth(ops):
    t=[0]*9
    for kind,ws in ops:
        v=max(t[i] for i in ws)+(kind=='ccx')
        for i in ws:t[i]=v
    return max(t)

def snapshot(state,products,goals):
    m=state_metrics(state.clean,products,goals)
    return dict(full_values=[hex(v) for v in state.values],clean_values=[hex(v) for v in state.clean],times=state.times,ops=state.ops,stages=state.stages,nonlinear_operations=sum(k=='ccx' for k,_ in state.ops),nonlinear_dependency_depth=nonlinear_depth(state.ops),metrics=m,full_affine_rank=len(s.pivots((ALL,*state.values))),clean_basis=[hex(v) for v in canonical(state.clean,s.FULL)])

def restore(data):
    state=State(tuple(int(v,16) for v in data['full_values']),tuple(data['times']),tuple((k,tuple(ws)) for k,ws in data['ops']),data['stages'])
    assert full_step(INITIAL,state.ops)==state.values
    assert state.clean==tuple(int(v,16) for v in data['clean_values'])
    assert s.timing((0,)*9,state.ops)==state.times
    return state

def search(w,side,seconds=15,beam=24,steps=20,seed=0,dedup='pareto',mix=False,mode='physical',aliases=4,exposure_limit=8,stage_width=1,initial=None):
    products,goals=s.bank(w,side);rng=random.Random(seed);start=time.monotonic();dom=Dominance(dedup)
    frontier=initial or [State(INITIAL,(0,)*9,())];archive={};history=[];expanded=0;best=None;timed_out=False
    def score(st):
        m=state_metrics(st.clean,products,goals)
        return (-m['rank_deficit']*30+len(m['present'])*8-m['remaining']*12+len(m['held'])+len(m['ready'])*.2+m['inputs']*.1-max(st.times)*.15)
    def save(st):
        key=(tuple(state_metrics(st.clean,products,goals)['present']),canonical(st.clean,s.FULL))
        if key not in archive or score(st)>score(archive[key]):archive[key]=st
    for st in frontier:save(st)
    for layer in range(steps):
        candidates=[]
        for state in frontier:
            if time.monotonic()-start>=seconds:timed_out=True;break
            met=state_metrics(state.clean,products,goals)
            if met['rank_deficit']==0:
                done=s.finish(state.clean,state.times,goals)
                if done:
                    tail,places,nt=done;ops=state.ops+tuple(tail);q=s.compile_ops(ops);report=s.verify(q,places,goals)
                    if best is None or report['depth']<best['report']['depth']:best=dict(report=report,ops=ops,qasm=qasm2.dumps(q))
                    continue
            ex=preimage_bank(state.values)
            for a,b,g in products:
                if time.monotonic()-start>=seconds:timed_out=True;break
                if a not in ex or b not in ex:continue
                for pre,p,r in exposures(state,a,b,goals,mode,aliases,exposure_limit,rng):
                    nv=full_step(state.values,pre)
                    assert restrict_clean(nv[p])==a and restrict_clean(nv[r])==b
                    for t in range(9):
                        if t in (p,r):continue
                        for other in ([None,*range(9)] if mix else [None]):
                            if other is not None and other in (p,r,t):continue
                            extra=() if other is None else (('cx',(t,other)),)
                            framed=full_step(nv,extra)
                            for packed in pack_options(framed,(('ccx',(p,r,t)),),products,stage_width):
                                tail=pre+extra+packed;out=full_step(state.values,tail);nt=s.timing(state.times,tail);expanded+=1
                                st=State(out,nt,state.ops+tail,state.stages+1)
                                if not dom.accept(st):continue
                                if not semantic_closure(canonical(st.clean,s.FULL),products,goals):continue
                                if state_metrics(st.clean,products,goals)['rank_deficit']==0:
                                    done=s.finish(st.clean,st.times,goals)
                                    if done:
                                        finish_ops,places,_=done;complete_ops=st.ops+tuple(finish_ops)
                                        q=s.compile_ops(complete_ops);checked=s.verify(q,places,goals)
                                        if best is None or checked['depth']<best['report']['depth']:
                                            best=dict(report=checked,ops=complete_ops,qasm=qasm2.dumps(q))
                                candidates.append((score(st)+rng.random()*.5,st))
                    if time.monotonic()-start>=seconds:timed_out=True;break
                if timed_out:break
            if timed_out:break
        candidates.sort(key=lambda v:v[0],reverse=True)
        selected=[];byspan={}
        for _,st in candidates:
            sk=canonical(st.clean,s.FULL)
            # Capacity cap is beam diversity, NEVER a dominance proof.
            if byspan.get(sk,0)>=max(2,beam//8):continue
            selected.append(st);byspan[sk]=byspan.get(sk,0)+1
            if len(selected)>=beam:break
        for st in selected:save(st)
        # Bound saved memory without throwing away the best prefixes per goal mask.
        if len(archive)>256:archive=dict(sorted(archive.items(),key=lambda kv:score(kv[1]),reverse=True)[:128])
        if selected:
            m=state_metrics(selected[0].clean,products,goals);history.append(dict(step=layer+1,expanded=expanded,depth=max(selected[0].times),**m))
        if timed_out or not selected:break
        frontier=selected
    partials=sorted(archive.values(),key=score,reverse=True)[:24]
    metrics=[state_metrics(st.clean,products,goals) for st in archive.values()]
    report=dict(status='complete' if best else ('timeout' if timed_out else 'bounded_search_finished'),elapsed=time.monotonic()-start,expanded=expanded,unique_semantic_spans=len(dom.spans),accepted_physical_states=dom.accepted,maximum_goals=max(len(m['present']) for m in metrics),best_rank_deficit=min(m['rank_deficit'] for m in metrics),maximum_held_products=max(len(m['held']) for m in metrics),best_suffix_estimate=min(m['remaining'] for m in metrics),history=history)
    return report,best,[snapshot(st,products,goals) for st in partials]

def run(config,outdir,initial=None):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=False);(outdir/'config.json').write_text(json.dumps(config,indent=2))
    w=json.loads(Path(config['witness']).read_text())
    from post190_xag_inplace_lower import outputs
    from post190_degree_rank_bound import targets
    assert all(outputs(w,x)==[t[x] for t in targets()[config['side']]] for x in range(64))
    report,best,partials=search(w,initial=initial,**{k:v for k,v in config.items() if k!='witness'})
    (outdir/'frontier.json').write_text(json.dumps(partials,indent=2))
    if best:
        text=best['qasm'];(outdir/'encoder.qasm').write_text(text);checked=s.verify(qasm2.loads(text),best['report']['outputs'],s.bank(w,config['side'])[1]);checked['sha256']=hashlib.sha256(text.encode()).hexdigest();report['best']=checked
        (outdir/'trajectory.json').write_text(json.dumps(best['ops'],indent=2))
    (outdir/'report.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='history'},flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--witness',required=True);p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--outdir',required=True);p.add_argument('--seconds',type=float,default=15);p.add_argument('--beam',type=int,default=24);p.add_argument('--steps',type=int,default=20);p.add_argument('--seed',type=int,default=0);p.add_argument('--dedup',choices=['span','physical','pareto'],default='pareto');p.add_argument('--mix',action='store_true');p.add_argument('--mode',choices=['physical','information'],default='physical');p.add_argument('--aliases',type=int,default=4);p.add_argument('--exposure-limit',type=int,default=8);p.add_argument('--stage-width',type=int,choices=[1,2,3],default=1);a=vars(p.parse_args());out=a.pop('outdir');run(a,out)
