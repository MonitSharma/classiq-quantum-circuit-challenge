"""Recover only demanded controls using the inverse trajectory's causal cone.

This is a physical recovery proposal generator for a known exact XAG, not a
generic truth-table circuit search. All selected gates are paid; a final
literal inverse still cancels every relative phase in the complete oracle.
"""
from __future__ import annotations
import argparse, hashlib, json, time
from itertools import combinations
from pathlib import Path
from destructive_phase_xag import State, apply, basis, represent, exposures, clock_ops, replay, emit
from post129_phase_rooted_xag import PhaseRooted, resume_state
from destructive_xag import load_xag
from md_xag import FULL, mask_indices, xor_mask
from distributed_frame_search import native
from qiskit import qasm2


def inverse_cone(forward, outputs):
    """Slice inverse(forward) backwards from its requested output wires.

    The reverse scan of the inverse is the original forward order. Gates with
    unneeded targets cannot affect the requested outputs; include controls as
    dependencies whenever a target is needed. Valid for arbitrary wire values.
    """
    needed=set(outputs);selected=[]
    for name,ws in forward:
        if name in ('z','cz'):continue
        assert name in ('x','cx','ccx')
        if ws[-1] in needed:
            selected.append((name,ws));needed.update(ws[:-1])
    return list(reversed(selected))


def orient_native(ops,clocks):
    """Choose symmetric control/CZ order by the paid primitive timeline.

    Swapping Margolus controls changes relative phases but preserves the
    Boolean permutation; the literal inverse emitter cancels those phases.
    """
    chosen=[]
    for name,ws in ops:
        options=[(name,ws)]
        if name in ('ccx','cz'):options.append((name,[ws[1],ws[0],*ws[2:]]))
        op=min(options,key=lambda op:(max(clock_ops(clocks,[op])),sum(clock_ops(clocks,[op]))))
        chosen.append(op);clocks=clock_ops(clocks,[op])
    return chosen,clocks


class SelectiveRecovery(PhaseRooted):
    def __init__(self,parsed,seed=0,max_forward=110,historical=True,orient=False,target_forms=False):
        super().__init__(parsed,seed,max_forward,suffix_recovery=False)
        self.historical=historical
        self.orient=orient
        self.target_forms=target_forms
        self.milestones={}

    def phase_ready(self,state):
        s=super().phase_ready(state)
        if self.max_forward is None or max(s.clocks)<=self.max_forward:
            count=s.phased_roots.bit_count();old=self.milestones.get(count)
            if old is None or max(s.clocks)<max(old.clocks):self.milestones[count]=s
        return s

    def algebraic_recovery(self,state):
        """Restore a lost input as an affine form plus ONE present-wire AND.

        The destination never occurs in a control or affine term. This is a
        reversible single-target update, not an assignment that erases a bit.
        """
        lost=set().union(*(p[3] for p in self.pressure(state))) if self.pressure(state) else set()
        out=[]
        for signal in sorted(lost):
            desired=self.signals[signal]
            for target in range(18):
                others=list(state.rows);others[target]=0;bp=basis(others)
                for a,b in combinations([w for w in range(18) if w!=target],2):
                    coeff=represent(bp,desired^state.rows[target]^(state.rows[a]&state.rows[b]))
                    if coeff is None:continue
                    prefix=[('cx',[w,target]) for w in mask_indices(coeff&((1<<18)-1))]
                    prefix.sort(key=lambda op:state.clocks[op[1][0]])
                    if coeff>>18&1:prefix.append(('x',[target]))
                    choices=[prefix+[('ccx',[a,b,target])],prefix+[('ccx',[b,a,target])]]
                    block=min(choices,key=lambda ops:max(clock_ops(state.clocks,ops)))
                    rows=apply(state.rows,block);assert rows[target]==desired
                    end=clock_ops(state.clocks,block)
                    if self.max_forward is not None and max(end)>self.max_forward:continue
                    nxt=State(rows,state.done,state.phase,state.phased_roots,state.ops+tuple(block),end,
                              state.history+({'algebraic_recovery':signal,'target':target,'gates':len(block)},))
                    out.append(self.phase_ready(nxt))
        return out

    def score(self,state):
        old=super().score(state)
        # When root availability ties, prefer a genuinely reusable direction
        # over another dirty AND that exposes no new demanded affine function.
        free=19-len(basis(state.rows))
        return (*old[:3],-free,*old[3:])

    def release_proposals(self,state):
        """Expose and erase a stored AND using its present logical controls.

        This need not reuse the physical controls or target of its creation.
        It is not a relative-phase cancellation claim: final literal inversion
        covers these operations along with the rest of the trajectory.
        """
        piv=basis(state.rows);out=[]
        for index,(left,right) in enumerate(self.operands):
            product=left&right
            if represent(piv,product) is None:continue
            if represent(piv,left) is None or represent(piv,right) is None:continue
            for _,_,pre,a,b,framed,clocks in exposures(state.rows,left,right,state.clocks,1):
                coeff=represent(basis(framed),product)
                for t in mask_indices(coeff&((1<<18)-1)):
                    if t in (a,b):continue
                    fix=[('cx',[w,t]) for w in mask_indices(coeff&((1<<18)-1)) if w!=t]
                    if coeff>>18&1:fix.append(('x',[t]))
                    prepared=apply(framed,fix)
                    assert prepared[t]==product and prepared[a]==left and prepared[b]==right
                    block=pre+fix+[('ccx',[a,b,t])];rows=apply(state.rows,block)
                    assert rows[t]==0
                    end=clock_ops(state.clocks,block)
                    if self.max_forward is not None and max(end)>self.max_forward:continue
                    nxt=State(rows,state.done,state.phase,state.phased_roots,state.ops+tuple(block),end,
                              state.history+({'semantic_release':index+13,'target':t,'gates':len(block)},))
                    out.append(self.phase_ready(nxt))
        return out

    def target_form_proposals(self,state):
        """Prepare a useful affine destination before the nonlinear toggle.

        If the next consumer needs P XOR (A AND B), physically expose P on the
        destination first. This avoids insisting that A AND B be stored alone.
        Control preparation and target preparation are both paid operations.
        """
        pending=self.pressure(state)[:2]
        needed=set().union(*(p[2] for p in pending)) if pending else set()
        consumers=needed|{p[1] for p in pending};piv=basis(state.rows);out=[]
        for signal in sorted(needed-self.terminal):
            left,right=self.operands[signal-13];product=left&right
            if represent(piv,product) is not None:continue
            if represent(piv,left) is None or represent(piv,right) is None:continue
            desireds={xor_mask(mask,self.signals) for consumer in consumers
                      for mask in self.forms[consumer-13] if mask>>signal&1}
            for _,_,pre,a,b,framed,clocks in exposures(state.rows,left,right,state.clocks,1):
                bp=basis(framed)
                for desired in desireds:
                    residual=desired^product
                    if represent(bp,residual) is None:continue
                    for t in range(18):
                        if t in (a,b):continue
                        others=list(framed);others[t]=0
                        coeff=represent(basis(others),framed[t]^residual)
                        if coeff is None:continue
                        fix=[('cx',[w,t]) for w in mask_indices(coeff&((1<<18)-1))]
                        fix.sort(key=lambda op:clocks[op[1][0]])
                        if coeff>>18&1:fix.append(('x',[t]))
                        block=pre+fix+[('ccx',[a,b,t])];rows=apply(state.rows,block)
                        assert rows[t]==desired and rows[a]==left and rows[b]==right
                        end=clock_ops(state.clocks,block)
                        if self.max_forward is not None and max(end)>self.max_forward:continue
                        nxt=State(rows,state.done|(1<<(signal-13)),state.phase,state.phased_roots,
                                  state.ops+tuple(block),end,state.history+(
                                      {'node':signal,'target':t,'target_operand':True,'block':block},))
                        out.append(self.phase_ready(nxt))
        return out

    def recovery_proposals(self,state):
        pending=self.pressure(state)
        if not pending:return []
        piv=basis(state.rows)
        lost=set().union(*(p[3] for p in pending))
        wanted={self.signals[s]:f'input_{s}' for s in lost}
        if self.historical:
            for _,root,missing,_ in pending[:3]:
                for i,value in enumerate(self.operands[root-13]):
                    if represent(piv,value) is None:wanted[value]=f'root_{root}_operand_{i}'
                for signal in missing:
                    if represent(piv,self.signals[signal]) is None:
                        wanted[self.signals[signal]]=f'node_{signal}'
        if not wanted:return []
        compute=[(name,ws) for name,ws in state.ops if name not in ('z','cz')]
        prefix=self.initial;found={}
        for cut in range(len(compute)):
            bp=basis(prefix)
            for desired,label in wanted.items():
                coeff=represent(bp,desired)
                if coeff is None:continue
                support=list(mask_indices(coeff&((1<<18)-1)))
                undo=inverse_cone(compute[cut:],support)
                if not undo:continue
                rows=apply(state.rows,undo)
                # The selected output wires must equal their prefix values;
                # other wires may retain useful work instead of being reset.
                assert all(rows[w]==prefix[w] for w in support)
                assert represent(basis(rows),desired) is not None
                end=clock_ops(state.clocks,undo)
                if self.max_forward is not None and max(end)>self.max_forward:continue
                signature=tuple((name,tuple(ws)) for name,ws in undo)
                if signature not in found:
                    nxt=State(rows,state.done,state.phase,state.phased_roots,state.ops+tuple(undo),end,
                              state.history+({'selective_recovery':label,'prefix_cut':cut,
                                              'gates':len(undo),'ccx':sum(n=='ccx' for n,_ in undo)},))
                    found[signature]=self.phase_ready(nxt)
            prefix=apply(prefix,[compute[cut]])
        return sorted(found.values(),key=self.score)

    def successors(self,state,exposure_limit=2):
        candidates=super().successors(state,exposure_limit)
        candidates+=self.recovery_proposals(state)
        candidates+=self.release_proposals(state)
        candidates+=self.algebraic_recovery(state)
        if self.target_forms:candidates+=self.target_form_proposals(state)
        if self.orient:
            retimed=[]
            for s in candidates:
                suffix,clocks=orient_native(s.ops[len(state.ops):],state.clocks)
                if clocks!=s.clocks:
                    variant=State(s.rows,s.done,s.phase,s.phased_roots,state.ops+tuple(suffix),clocks,s.history)
                    retimed.append(self.phase_ready(variant))
            candidates+=retimed
        # phase_ready can add gates after the proposal's preliminary cap test.
        # Enforce the cap on the complete physical suffix, including those taps.
        if self.max_forward is not None:
            candidates=[s for s in candidates if max(s.clocks)<=self.max_forward]
        self.rng.shuffle(candidates)
        return sorted(candidates,key=lambda s:(self.score(s),sum(s.clocks)))


def save_trace(path,s,r):
    path.write_text(json.dumps(dict(**r,ops=s.ops,history=s.history,phase_mask=s.phased_roots,
                                    semantic_phase_hex=hex(s.phase)),indent=2)+'\n')


def campaign(out,resume,trials=10,seconds=10,beam=4,cap=110,historical=True,orient=False,target_forms=False):
    assert not out.exists();out.mkdir(parents=True)
    source=Path('artifacts/multiplicative_depth/optimized/advanced_round4.xag')
    parsed=load_xag(source);results=[];best=None;best_score=None;milestones={}
    (out/'config.json').write_text(json.dumps(dict(source=str(source),resume=str(resume),
        resume_sha256=hashlib.sha256(resume.read_bytes()).hexdigest(),trials=trials,seconds=seconds,
        beam=beam,cap=cap,historical=historical,orient=orient,target_forms=target_forms,
        compiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
    for seed in range(trials):
        lower=SelectiveRecovery(parsed,seed,cap,historical,orient,target_forms);initial=resume_state(lower,resume)
        s,r=lower.run_rooted(seconds=seconds,beam=beam,steps=100,initial=initial)
        exact=replay(s,lower.initial,lower.target)
        r.update(seed=seed,phased_roots=s.phased_roots.bit_count(),forward_native_depth=max(s.clocks),
                 exact=exact,selective_recoveries=sum('selective_recovery' in h for h in s.history),
                 nearest_root_pressure=lower.pressure(s)[0][0][:3] if lower.pressure(s) else [])
        assert max(s.clocks)<=cap
        results.append(r);score=lower.score(s)
        if best is None or score<best_score:
            best,best_score=s,score;save_trace(out/'best.json',s,r);print(r,flush=True)
        for count,candidate in lower.milestones.items():
            if max(candidate.clocks)<milestones.get(count,float('inf')):
                assert replay(candidate,lower.initial,lower.target)==(candidate.phase==lower.target or candidate.phase^lower.target==FULL)
                milestones[count]=max(candidate.clocks)
                info=dict(seed=seed,phased_roots=count,forward_native_depth=max(candidate.clocks),
                          exact=candidate.phase==lower.target,source='all generated candidates within cap')
                save_trace(out/f'roots_{count}.json',candidate,info)
        r['minimum_depth_by_roots']={k:max(v.clocks) for k,v in lower.milestones.items()}
        (out/'report.json').write_text(json.dumps(results,indent=2)+'\n')
        if exact:
            from exhaustive_verify import exhaustive
            raw=emit(s,18);q=min([raw,native(raw)],key=lambda q:q.depth())
            path=out/f'exact_{seed}.qasm';path.write_text(qasm2.dumps(q));exhaustive(path)
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--resume',type=Path,default=Path('artifacts/post129_phase_rooted_longer/best.json'))
    p.add_argument('--trials',type=int,default=10);p.add_argument('--seconds',type=float,default=10)
    p.add_argument('--beam',type=int,default=4);p.add_argument('--cap',type=int,default=110)
    p.add_argument('--inputs-only',action='store_true');p.add_argument('--orient',action='store_true')
    p.add_argument('--target-forms',action='store_true');a=p.parse_args()
    campaign(a.outdir,a.resume,a.trials,a.seconds,a.beam,a.cap,not a.inputs_only,a.orient,a.target_forms)
