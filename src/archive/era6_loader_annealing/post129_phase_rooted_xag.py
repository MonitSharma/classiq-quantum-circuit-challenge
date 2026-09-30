"""Backward phase-demand search over 18 mutable physical Boolean registers.

Known exact XAG only. Nine terminal roots of advanced_round4 are CZ demands,
not materialized nodes. Reuses the paid native timing and literal-inverse
emitter, and searches for operand exposure rather than a high node count.
"""
from __future__ import annotations
import argparse,json,random,time,hashlib
from pathlib import Path

from qiskit import QuantumCircuit,qasm2
from destructive_xag import load_xag
from destructive_phase_xag import Lowerer,State,basis,represent,apply,exposures,clock_ops,emit,replay
from md_xag import FULL,mask_indices,xor_mask
from distributed_frame_search import native


class PhaseRooted(Lowerer):
    def __init__(self,parsed,seed=0,max_forward=120,suffix_recovery=False):
        super().__init__(parsed,relaxed=True,max_forward=max_forward)
        self.rng=random.Random(seed)
        self.terminal={r for r in self.roots if not self.users[r-13]}
        self.root_order=self.roots.copy();self.rng.shuffle(self.root_order)
        self.root_priority={r:i for i,r in enumerate(self.root_order)}
        self.cached={}
        self.suffix_recovery=suffix_recovery

    def demand(self,state,root,piv=None):
        """Backward-slice only unavailable affine operands of a phase root."""
        piv=basis(state.rows) if piv is None else piv
        missing=set();lost=set();visited=set()
        def visit_form(mask):
            if represent(piv,xor_mask(mask,self.signals)) is not None:return
            for signal in mask_indices(mask):
                if represent(piv,self.signals[signal]) is not None:continue
                if signal<13:lost.add(signal);continue
                if signal in visited:continue
                visited.add(signal)
                a,b=self.forms[signal-13]
                visit_form(a);visit_form(b);missing.add(signal)
        a,b=self.forms[root-13];visit_form(a);visit_form(b)
        exposed=sum(represent(piv,v) is not None for v in self.operands[root-13])
        return missing,lost,exposed

    def pressure(self,state):
        key=(state.rows,state.phased_roots)
        if key in self.cached:return self.cached[key]
        piv=basis(state.rows);pending=[]
        for i,root in enumerate(self.roots):
            if state.phased_roots>>i&1:continue
            missing,lost,exposed=self.demand(state,root,piv)
            pending.append(((len(lost),len(missing),-exposed,self.root_priority[root]),root,missing,lost))
        pending.sort(key=lambda x:x[0])
        self.cached[key]=pending
        return pending

    def score(self,state):
        if state.phase==self.target:return (-100,0,0,0,0)
        pending=self.pressure(state)
        if not pending:return (-state.phased_roots.bit_count(),0,0,max(state.clocks),0)
        metric=pending[0][0]
        # Missing inputs are recovery debt, not automatic infeasibility.
        return (-state.phased_roots.bit_count(),metric[0],metric[1],max(state.clocks),metric[2])

    def phase_ready(self,state):
        state=self.phase_available(state)
        if state.phase==self.target:return state
        # All output products may contribute CZ without storage. Nonterminal
        # output nodes remain available for later materialization if demanded.
        for root in self.root_order:
            ri=self.roots.index(root)
            if state.phased_roots>>ri&1:continue
            left,right=self.operands[root-13]
            choices=exposures(state.rows,left,right,state.clocks,1)
            if not choices:continue
            _,_,pre,a,b,rows,clocks=choices[0]
            ops=pre+[('cz',[a,b])]
            state=State(rows,state.done,state.phase^(left&right),state.phased_roots|(1<<ri),
                        state.ops+tuple(ops),clock_ops(clocks,[('cz',[a,b])]),
                        state.history+({'node':root,'phase_only':True,'pre':pre},))
            if state.phase==self.target:return state
        return self.phase_available(state)

    def successors(self,state,exposure_limit=2):
        pending=self.pressure(state)
        # Explore demands of the nearest two roots, retaining cross-root sharing.
        needed=set().union(*(item[2] for item in pending[:2])) if pending else set()
        needed-=self.terminal
        piv=basis(state.rows);candidates=[]
        for signal in sorted(needed):
            left,right=self.operands[signal-13]
            if represent(piv,left) is None or represent(piv,right) is None:continue
            product=left&right
            if represent(piv,product) is not None:continue
            for _,_,pre,a,b,framed,clocks in exposures(state.rows,left,right,state.clocks,exposure_limit):
                for t in range(18):
                    if t in (a,b):continue
                    rows=list(framed);rows[t]^=product
                    block=pre+[('ccx',[a,b,t])]
                    nxt=State(tuple(rows),state.done|(1<<(signal-13)),state.phase,state.phased_roots,
                              state.ops+tuple(block),clock_ops(clocks,[('ccx',[a,b,t])]),
                              state.history+({'node':signal,'target':t,'dirty':bool(framed[t]),'block':block},))
                    candidates.append(self.phase_ready(nxt))
        # Paid inverse blocks can recover overwritten input/control forms.
        # They are evaluated on the actual current rows; no assumed identities.
        old_score=self.score(state)
        for item in state.history[-8:]:
            if 'block' not in item:continue
            undo=list(reversed(item['block']));rows=apply(state.rows,undo)
            nxt=State(rows,state.done,state.phase,state.phased_roots,state.ops+tuple(undo),
                      clock_ops(state.clocks,undo),state.history+({'recovery_of':item['node']},))
            nxt=self.phase_ready(nxt)
            if self.score(nxt)[:3]<old_score[:3]:candidates.append(nxt)
        if self.suffix_recovery:
            # Phase gates stay deposited. Undo an actual non-diagonal suffix,
            # including any control-frame changes, to recover earlier storage.
            # Neutral demand moves are necessary to release obsolete values.
            compute=[op for op in state.ops if op[0] not in ('z','cz')]
            cuts=sorted({0,*[i for i,(name,_) in enumerate(compute) if name=='ccx'][-8:]})
            for cut in cuts:
                undo=list(reversed(compute[cut:]));rows=apply(state.rows,undo)
                if rows==state.rows:continue
                nxt=State(rows,state.done,state.phase,state.phased_roots,state.ops+tuple(undo),
                          clock_ops(state.clocks,undo),
                          state.history+({'suffix_recovery':len(undo)},))
                nxt=self.phase_ready(nxt)
                if self.score(nxt)[:3]<=old_score[:3]:candidates.append(nxt)
        if self.max_forward is not None:candidates=[s for s in candidates if max(s.clocks)<=self.max_forward]
        self.rng.shuffle(candidates)
        return sorted(candidates,key=self.score)

    def run_rooted(self,seconds=2,beam=4,steps=100,initial=None):
        start=time.monotonic();first=self.phase_ready(initial or self.initial_state());frontier=[first];best=first
        seen={};expanded=0;status='step_limit'
        for step in range(steps):
            out=[]
            for state in frontier:
                if state.phase==self.target:return state,dict(status='exact',expanded=expanded,seconds=time.monotonic()-start)
                if time.monotonic()-start>=seconds:status='time_limit';break
                out+=self.successors(state)[:beam];expanded+=1
            if not out:status='restricted_search_stalled';break
            unique={}
            for s in out:
                key=(s.rows,s.phased_roots)
                if seen.get(key,float('inf'))<=max(s.clocks):continue
                if key not in unique or max(s.clocks)<max(unique[key].clocks):unique[key]=s
            if not unique:status='restricted_search_stalled';break
            frontier=sorted(unique.values(),key=self.score)[:beam]
            best=min([best,*frontier],key=self.score)
            for s in frontier:seen[(s.rows,s.phased_roots)]=max(s.clocks)
            if time.monotonic()-start>=seconds:status='time_limit';break
        return best,dict(status=status,expanded=expanded,seconds=time.monotonic()-start)


def reference_complete(parsed,order=None):
    """Complete phase-demand control, frozen-coordinate allocation only.

    This is an explicitly labeled reference, not the destructive search. It
    clears each cone by reversing its known witness before the next root.
    Each compute block is paired with its literal inverse when released.
    """
    from xag_to_inplace_layers import XAGGraph
    from xag import plan,linear_best
    graph=XAGGraph(parsed.nodes)
    roots=[s for s in mask_indices(parsed.output_affine_mask) if s>=13]
    order=list(order or roots)
    q=QuantumCircuit(18);wire={i:i for i in range(12)};live=set();free=list(range(12,18))
    for s in mask_indices(parsed.output_affine_mask):
        if 1<=s<=12:q.z(s-1)
    toggles=0;plans=[]
    def toggle(v):
        nonlocal toggles
        toggles+=1
        if v in live:
            # Rebuild current affine controls: other named inputs may have been
            # released and recomputed on different physical registers.
            release=True;target=wire[v]
        else:release=False;target=free.pop(0)
        node=parsed.nodes[v-13]
        forms=[frozenset(-1 if s==0 else s-1 if s<=12 else s for s in mask_indices(m))
               for m in [node.left_affine_mask,node.right_affine_mask]]
        pre,a,b=linear_best(None,*forms,wire)
        block=pre.copy();block.rccx(a,b,target);block.compose(pre.inverse(),inplace=True)
        q.compose(block.inverse() if release else block,inplace=True)
        if release:live.remove(v);free.append(wire.pop(v));free.sort()
        else:live.add(v);wire[v]=target
    for root in order:
        sequence=plan(graph,frozenset(),graph.nodes[root],limit=6,max_states=60000)
        for v in sequence:toggle(v)
        n=parsed.nodes[root-13]
        forms=[frozenset(-1 if s==0 else s-1 if s<=12 else s for s in mask_indices(m))
               for m in [n.left_affine_mask,n.right_affine_mask]]
        pre,a,b=linear_best(None,*forms,wire);q.compose(pre,inplace=True);q.cz(a,b);q.compose(pre.inverse(),inplace=True)
        plans.append({'root':root,'toggles':sequence,'live':sorted(live)})
        for v in reversed(sequence):toggle(v)
    assert not live
    return native(q),dict(kind='complete independent phase-cone reference; inputs frozen',toggles=toggles,order=order,plans=plans)


def resume_state(lower,path):
    """Restore a saved physical trajectory, checking all 4096 input values."""
    data=json.loads(path.read_text());ops=tuple((name,ws) for name,ws in data['ops'])
    phase=xor_mask(lower.parsed.output_affine_mask&((1<<13)-1),lower.signals)
    for i,root in enumerate(lower.roots):
        if data['phase_mask']>>i&1:phase^=lower.signals[root]
    if 'semantic_phase_hex' in data:phase=int(data['semantic_phase_hex'],16)
    s=State(apply(lower.initial,ops),0,phase,data['phase_mask'],ops,
            clock_ops((0,)*18,ops),tuple(data['history']))
    replay(s,lower.initial,lower.target)
    return s


def campaign(out,trials=100,seconds=1,beam=4,cap=120,suffix_recovery=False,resume=None):
    assert not out.exists();out.mkdir(parents=True)
    source=Path('artifacts/multiplicative_depth/optimized/advanced_round4.xag');parsed=load_xag(source)
    inventory=PhaseRooted(parsed)
    (out/'inventory.json').write_text(json.dumps(dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        nodes=len(parsed.nodes),roots=inventory.roots,terminal=sorted(inventory.terminal),compute_nodes=len(parsed.nodes)-len(inventory.terminal),
        trials=trials,seconds_per_trial=seconds,beam=beam,forward_cap=cap,suffix_recovery=suffix_recovery,
        compiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        resume=str(resume) if resume else None,
        resume_sha256=hashlib.sha256(resume.read_bytes()).hexdigest() if resume else None),indent=2)+'\n')
    rows=[];best=None;bestkey=None
    for seed in range(trials):
        lower=PhaseRooted(parsed,seed,cap,suffix_recovery)
        initial=resume_state(lower,resume) if resume else None
        s,r=lower.run_rooted(seconds,beam,initial=initial)
        exact=replay(s,lower.initial,lower.target)
        r.update(seed=seed,phased_roots=s.phased_roots.bit_count(),forward_native_depth=max(s.clocks),exact=exact,
                 dirty_coordinate_targets=sum(h.get('dirty',False) and h.get('target',18)<12 for h in s.history),
                 recoveries=sum('recovery_of' in h or 'suffix_recovery' in h for h in s.history),
                 nearest_root_pressure=lower.pressure(s)[0][0][:3] if lower.pressure(s) else [])
        rows.append(r);key=lower.score(s)
        if best is None or key<bestkey:
            best,bestkey=s,key
            (out/'best.json').write_text(json.dumps(dict(**r,ops=s.ops,history=s.history,phase_mask=s.phased_roots),indent=2)+'\n')
            print(r,flush=True)
        (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n')
        if exact:
            from exhaustive_verify import exhaustive
            raw=emit(s,18);q=min([raw,native(raw)],key=lambda q:q.depth());p=out/f'exact_{seed}.qasm'
            p.write_text(qasm2.dumps(q));exhaustive(p)
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--trials',type=int,default=100);p.add_argument('--seconds',type=float,default=1)
    p.add_argument('--beam',type=int,default=4);p.add_argument('--cap',type=int,default=120)
    p.add_argument('--reference',action='store_true');p.add_argument('--suffix-recovery',action='store_true')
    p.add_argument('--resume',type=Path);a=p.parse_args()
    if a.reference:
        assert not a.outdir.exists();a.outdir.mkdir(parents=True)
        parsed=load_xag(Path('artifacts/multiplicative_depth/optimized/advanced_round4.xag'))
        q,r=reference_complete(parsed);path=a.outdir/'oracle.qasm';path.write_text(qasm2.dumps(q))
        from exhaustive_verify import exhaustive
        exhaustive(path);r.update(depth=q.depth(),cx=q.count_ops().get('cx',0))
        (a.outdir/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    else:campaign(a.outdir,a.trials,a.seconds,a.beam,a.cap,a.suffix_recovery,a.resume)
