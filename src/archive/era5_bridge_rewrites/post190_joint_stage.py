"""True simultaneous seeded RCCX stages in a shared affine register frame.

Semantic dedup is by FULL affine span. It has no physical-cost dominance
meaning. All quotient bases and retained subspaces are enumerated exactly for
each visited independent control tuple; bounded searches may stop mid-stream.
"""
import argparse,functools,itertools,json,time,heapq,hashlib
from collections import Counter,deque
from dataclasses import dataclass
from pathlib import Path
from qiskit import qasm2
import post190_information_space as info
import post190_semantic_register as sem

@functools.lru_cache(65536)
def basis(rows):
    p=sem.pivots(rows)
    for b in sorted(p):
        for c in p:
            if c>b and p[c]>>b&1:p[c]^=p[b]
    return tuple(p[b] for b in sorted(p,reverse=True))

def independent_controls(masks):return len(basis(tuple(m&511 for m in masks)))==len(masks)

def combine(rows,mask):
    v=0
    for j,row in enumerate(rows):
        if mask>>j&1:v^=row
    return v

@functools.lru_cache(4096)
def subspaces(n,d):
    """Every d-subspace of GF(2)^n once, by reduced row echelon matrices."""
    out=[]
    for piv in itertools.combinations(range(n),d):
        slots=[(r,c) for r,p in enumerate(piv) for c in range(p+1,n) if c not in piv]
        for assignment in range(1<<len(slots)):
            rows=[1<<p for p in piv]
            for j,(r,c) in enumerate(slots):
                if assignment>>j&1:rows[r]|=1<<c
            out.append(tuple(rows))
    return tuple(out)

@functools.lru_cache(32768)
def quotient_basis(retained,n=9):
    rows=list(retained);extra=[]
    for j in range(n):
        v=1<<j
        if len(basis(tuple(rows+[v])))>len(rows):rows.append(v);extra.append(v)
    assert len(rows)==n
    return tuple(extra)

@functools.lru_cache(1024)
def ordered_quotient_bases(k):
    return tuple(rows for rows in itertools.permutations(range(1,1<<k),k) if len(basis(rows))==k)

@functools.lru_cache(8192)
def enumerate_retained_subspaces(control_basis,k):
    """Return H with spectators, and quotient representatives V/H.

For width2: [5 choose3]_2 =155 retained H; width3: H=C only.
Adding H to a target representative does not change its successor affine span.
"""
    assert len(control_basis)==2*k
    complement=quotient_basis(control_basis)
    out=[]
    for coefficients in subspaces(9-2*k,9-3*k):
        spectators=tuple(combine(complement,row) for row in coefficients)
        h=basis(control_basis+spectators)
        assert len(h)==9-k
        out.append((h,spectators,quotient_basis(h)))
    return tuple(out)


def joint_control_aliases(values,products,selected,stats=None):
    ex=info.preimage_bank(values);seen=set()
    options=[tuple(m for _,m in ex[v]) for j in selected for v in products[j][:2]]
    def recurse(pos,masks):
        if pos==len(options):
            full=tuple(info.evaluate_mask(values,m) for m in masks)
            prods=tuple(full[j]&full[j+1] for j in range(0,len(full),2))
            cb=basis(tuple(m&511 for m in masks))
            key=(cb,prods,tuple(m>>9 for m in masks))
            if key not in seen:
                seen.add(key)
                if stats is not None:stats['independent_alias_combinations']+=1;stats[f'width{len(selected)}_independent_control_sets']+=1
                yield tuple(masks),cb,prods
            return
        for m in options[pos]:
            if independent_controls((*masks,m)):yield from recurse(pos+1,(*masks,m))
    yield from recurse(0,())


def apply_joint_transition(values,controls,spectators,targets):
    """One simultaneous nonlinear transition, never sequential semantic updates."""
    k=len(targets);frame=tuple(controls)+tuple(targets)+tuple(spectators)
    assert len(frame)==9 and independent_controls(frame)
    pre=tuple(info.evaluate_mask(values,m) for m in frame)
    products=tuple(pre[2*j]&pre[2*j+1] for j in range(k))
    successor=pre[:2*k]+tuple(pre[2*k+j]^products[j] for j in range(k))+pre[3*k:]
    return successor,frame,products


def reconstruct_joint_frame(values,record):
    masks=tuple(record['frame']);pre=info.frame_ops(masks);k=len(record['selected_products'])
    gates=tuple(('ccx',(2*j,2*j+1,2*k+j)) for j in range(k))
    assert len({w for _,ws in gates for w in ws})==3*k
    out=info.full_step(values,pre+gates)
    return pre+gates,out


def joint_stage_successors(values,products,widths=(3,2),stats=None):
    stats=stats if stats is not None else Counter();ex=info.preimage_bank(values)
    eligible=[j for j,(a,b,g) in enumerate(products) if a in ex and b in ex]
    stats['states_expanded']+=1
    # Round-robin product sets avoids starving later triples with a large alias bank.
    for k in widths:
        tasks=[]
        for selected in itertools.combinations(eligible,k):
            stats[{1:'products_considered',2:'product_pairs_considered',3:'product_triples_considered'}[k]]+=1
            tasks.append((selected,iter(joint_control_aliases(values,products,selected,stats))))
        while tasks:
            next_tasks=[]
            for selected,aliases in tasks:
                try:controls,cb,full_products=next(aliases)
                except StopIteration:continue
                next_tasks.append((selected,aliases))
                for h,spectators,q in enumerate_retained_subspaces(cb,k):
                    stats['H_subspaces_enumerated']+=1
                    for qb in ordered_quotient_bases(k):
                        targets=tuple(combine(q,v) for v in qb)
                        successor,frame,actual=apply_joint_transition(values,controls,spectators,targets)
                        assert actual==full_products
                        stats['transitions_generated']+=1;stats[f'width{k}_transitions']+=1
                        record=dict(selected_products=selected,control_aliases=controls,H=h,spectators=spectators,quotient_representatives=q,ordered_quotient_basis=qb,targets=targets,frame=frame,full_products=[hex(t) for t in full_products])
                        yield successor,record
            tasks=next_tasks

@functools.lru_cache(65536)
def relaxed_stage_bound(clean_basis,products,goals):
    """Admissible synchronous bound: unlimited capacity, all eligible products.

Every legal stage can add only products with operands in its starting span.
Induction embeds any actual successor span in this relaxed growing span.
"""
    values=list(clean_basis)
    for depth in range(len(products)+2):
        p=sem.pivots(values)
        if all(sem.contains(p,g) for g in goals):return depth
        new=[g for a,b,g in products if sem.contains(p,a) and sem.contains(p,b) and not sem.contains(p,g)]
        if not new:return 100000
        values+=new
    return 100000

@dataclass
class Node:
    values:tuple
    path:tuple
    origin:int
    @property
    def clean(self):return tuple(map(info.restrict_clean,self.values))


def reconstruct(node,initial,products,goals,outdir):
    st=initial[node.origin];values=st.values;ops=st.ops
    for record in node.path:
        tail,values=reconstruct_joint_frame(values,record);ops+=tail
    assert values==node.values
    met=info.state_metrics(tuple(map(info.restrict_clean,values)),products,goals)
    if met['rank_deficit']:return None
    done=sem.finish(tuple(map(info.restrict_clean,values)),sem.timing((0,)*9,ops),goals)
    assert done is not None
    tail,places,_=done;ops+=tuple(tail);q=sem.compile_ops(ops);text=qasm2.dumps(q)
    (outdir/'encoder.qasm').write_text(text);report=sem.verify(qasm2.loads(text),places,goals)
    report.update(sha256=hashlib.sha256(text.encode()).hexdigest(),nonlinear_operations=sum(k=='ccx' for k,_ in ops),joint_suffix_stages=len(node.path),prefix_stages=st.stages)
    (outdir/'verification.json').write_text(json.dumps(report,indent=2))
    return report


def search(initial,products,goals,outdir,stages=1,seconds=20,policy='bfs',max_states=200000,widths=(3,2),burst=0,relaxed_prune=False):
    start=time.monotonic();stats=Counter();seen={};queue=[];serial=0;best=None;complete=None;memory_limited=False;archive={};expanded_depths=Counter();improving_control_sets=set();saved_widths=set()
    @functools.lru_cache(65536)
    def metric(values):return info.state_metrics(tuple(map(info.restrict_clean,values)),products,goals)
    def priority(node):
        m=metric(node.values)
        return (m['rank_deficit'],-len(m['present']),m['remaining'],-len(m['ready']),len(node.path))
    def push(node,iterator=None):
        nonlocal serial
        key=(len(node.path),serial) if policy=='bfs' else (*priority(node),serial)
        heapq.heappush(queue,(key,node,iterator));serial+=1
    for j,st in enumerate(initial):
        node=Node(st.values,(),j);push(node);seen[info.canonical(st.values,info.ALL)]=0
    status='exhausted_requested_depth'
    while queue:
        if time.monotonic()-start>seconds:status='timeout';break
        _,node,iterator=heapq.heappop(queue)
        if best is None or priority(node)<priority(best):best=node
        if len(node.path)>=stages:continue
        if relaxed_prune and relaxed_stage_bound(info.canonical(node.clean,sem.FULL),products,goals)>stages-len(node.path):
            stats['relaxed_bound_pruned_parents']+=1;continue
        if iterator is None:
            expanded_depths[len(node.path)]+=1
            iterator=iter(joint_stage_successors(node.values,products,widths,stats))
        parent_deficit=metric(node.values)['rank_deficit']
        generated_in_burst=0
        for values,record in iterator:
            if time.monotonic()-start>seconds:status='timeout';break
            generated_in_burst+=1
            k=len(record['selected_products']);m=metric(values)
            stats['best_goal_rank_improvement']=max(stats['best_goal_rank_improvement'],parent_deficit-m['rank_deficit'])
            if k==3:
                stats['width3_best_rank_improvement']=max(stats['width3_best_rank_improvement'],parent_deficit-m['rank_deficit'])
                if m['rank_deficit']<parent_deficit:
                    stats['width3_rank_improving_transitions']+=1
                    improving_control_sets.add((node.values,tuple(record['control_aliases']),tuple(record['full_products'])))
                    stats['width3_rank_improving_control_sets']=len(improving_control_sets)
            key=info.canonical(values,info.ALL)
            if seen.get(key,10**9)<=len(node.path)+1:continue
            seen[key]=len(node.path)+1;stats[f'width{k}_unique_successors']+=1
            record['successor_span']=[hex(t) for t in key]
            if k not in saved_widths:
                saved_widths.add(k)
                example=dict(initial=info.snapshot(initial[node.origin],products,goals),path=node.path+(record,),final_values=[hex(t) for t in values])
                (outdir/f'example_width{k}.json').write_text(json.dumps(example,indent=2))
            nxt=Node(values,node.path+(record,),node.origin)
            if best is None or priority(nxt)<priority(best):best=nxt
            # Retain partial representatives by clean span, for reporting only.
            ck=info.canonical(nxt.clean,sem.FULL)
            if len(archive)<256 or (best is nxt):archive[ck]=nxt
            if m['rank_deficit']==0:
                complete=nxt;status='semantic_complete';break
            if len(nxt.path)<stages:
                if relaxed_prune and relaxed_stage_bound(ck,products,goals)>stages-len(nxt.path):
                    stats['relaxed_bound_pruned_successors']+=1
                elif len(queue)<max_states:push(nxt)
                else:memory_limited=True;stats['queue_capacity_drops']+=1
            if burst and generated_in_burst>=burst:
                push(node,iterator);stats['suspended_expansions']+=1;break
        if status in ('timeout','semantic_complete'):break
    if memory_limited and status=='exhausted_requested_depth':status='queue_limited_finished'
    assert best is not None
    report=dict(status=status,elapsed=time.monotonic()-start,**stats,unique_full_spans=len(seen),expanded_depths=dict(expanded_depths),queued_unexpanded=len(queue),best_metrics=metric(best.values),best_suffix_stages=len(best.path),queue_limited=memory_limited)
    chosen=complete or best
    payload=dict(origin=chosen.origin,initial=info.snapshot(initial[chosen.origin],products,goals),path=chosen.path,final_values=[hex(t) for t in chosen.values],metrics=metric(chosen.values))
    (outdir/('completion.json' if complete else 'best_partial.json')).write_text(json.dumps(payload,indent=2))
    if complete:report['encoder']=reconstruct(complete,initial,products,goals,outdir)
    (outdir/'report.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--witness',default='artifacts/post190_nist_variants_wide/y_candidate_0.json');p.add_argument('--side',choices=['x','y'],default='y');p.add_argument('--frontier');p.add_argument('--prefix-index',type=int,default=0);p.add_argument('--outdir',required=True);p.add_argument('--stages',type=int,default=1);p.add_argument('--seconds',type=float,default=20);p.add_argument('--policy',choices=['bfs','best'],default='bfs');p.add_argument('--max-states',type=int,default=200000);p.add_argument('--widths',default='3,2');p.add_argument('--burst',type=int,default=0);p.add_argument('--relaxed-prune',action='store_true');a=p.parse_args();out=Path(a.outdir);out.mkdir(parents=True,exist_ok=False);(out/'config.json').write_text(json.dumps(vars(a),indent=2))
    w=json.loads(Path(a.witness).read_text());products,goals=sem.bank(w,a.side)
    from post190_degree_rank_bound import targets
    from post190_xag_inplace_lower import outputs
    assert all(outputs(w,x)==[t[x] for t in targets()[a.side]] for x in range(64))
    initial=[info.restore(json.loads(Path(a.frontier).read_text())[a.prefix_index])] if a.frontier else [info.State(info.INITIAL,(0,)*9,())]
    search(initial,products,goals,out,a.stages,a.seconds,a.policy,a.max_states,tuple(map(int,a.widths.split(','))),a.burst,a.relaxed_prune)

if __name__=='__main__':main()
