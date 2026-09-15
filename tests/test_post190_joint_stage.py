import json,itertools
from pathlib import Path
from collections import Counter
import post190_joint_stage as j
import post190_information_space as i
import post190_semantic_register as s


def test_small_subspace_and_quotient_counts():
    assert len(j.subspaces(5,3))==155
    assert len({j.basis(rows) for rows in j.subspaces(5,3)})==155
    assert len(j.ordered_quotient_bases(2))==6
    assert len(j.ordered_quotient_bases(3))==168
    for k in (2,3):
        c=j.basis(tuple(1<<r for r in range(2*k)))
        retained=j.enumerate_retained_subspaces(c,k)
        assert len(retained)==(155 if k==2 else 1)
        for h,spec,q in retained:
            assert len(h)==9-k and len(q)==k
            assert len(j.basis(h+q))==9
            assert all(s.contains(s.pivots(h),m) for m in c)


def test_joint_width_two_and_three_exact_full_semantics():
    for k in (2,3):
        controls=tuple((1<<r)^(512 if r%2 else 0) for r in range(2*k))
        cb=j.basis(tuple(m&511 for m in controls));h,spec,q=j.enumerate_retained_subspaces(cb,k)[0]
        for qb in j.ordered_quotient_bases(k):
            targets=tuple(j.combine(q,m) for m in qb)
            out,frame,products=j.apply_joint_transition(i.INITIAL,controls,spec,targets)
            rec=dict(frame=frame,selected_products=list(range(k)))
            ops,physical=j.reconstruct_joint_frame(i.INITIAL,rec)
            assert out==physical
            assert i.canonical(out,i.ALL)==i.canonical(physical,i.ALL)
            assert len(j.basis(out))==9
            assert len(set(w for kind,ws in ops if kind=='ccx' for w in ws))==3*k


def test_controls_with_overlapping_masks_are_independent():
    masks=(3,6,12,24,48,32)
    assert j.independent_controls(masks)
    assert not j.independent_controls((*masks[:5],masks[0]^masks[1]))


def test_joint_frame_exposes_triple_old_first_packer_misses():
    masks=(3,6,12,24,48,32)
    controls=tuple(i.evaluate_mask(i.INITIAL,m) for m in masks)
    products=tuple((i.restrict_clean(controls[r]),i.restrict_clean(controls[r+1]),i.restrict_clean(controls[r]&controls[r+1])) for r in (0,2,4))
    _,_,pre,p,r=i.broad_expose(masks[0],masks[1],(0,)*9,1)[0]
    old_frame=i.full_step(i.INITIAL,pre)
    # Even with every legal first target, opportunistic packer cannot pack3.
    assert all(len(stage)<3 for t in range(9) if t not in (p,r) for stage in i.pack_options(old_frame,(('ccx',(p,r,t)),),products,3))
    out,frame,_=j.apply_joint_transition(i.INITIAL,masks,(),(64,128,256))
    ops,physical=j.reconstruct_joint_frame(i.INITIAL,dict(frame=frame,selected_products=(0,1,2)))
    assert out==physical
    # All three code products plus raw may be materialized in a real circuit.
    goals=tuple(v[2] for v in products)+(s.INPUTS[5],)
    done=s.finish(tuple(map(i.restrict_clean,out)),s.timing((0,)*9,ops),goals)
    assert done
    tail,places,_=done;q=s.compile_ops(ops+tuple(tail));r=s.verify(q,places,goals)
    assert r['checked_inputs']==64
    assert s.compile_ops([('ccx',(0,1,6)),('ccx',(2,3,7)),('ccx',(4,5,8))]).depth()==7


def test_alias_backtracking_and_prefix_snapshot_replay():
    w=json.loads(Path('artifacts/post190_nist_variants_wide/y_candidate_0.json').read_text());p,g=s.bank(w,'y')
    data=json.loads(Path('artifacts/post190_information_space/comparison_cached/B/frontier.json').read_text())[0];st=i.restore(data)
    eligible=[n for n,(a,b,_) in enumerate(p) if a in i.preimage_bank(st.values) and b in i.preimage_bank(st.values)]
    sets=[]
    for selected in itertools.combinations(eligible,3):
        for controls,cb,products in j.joint_control_aliases(st.values,p,selected):
            assert len(cb)==6 and j.independent_controls(controls);sets.append(selected)
    assert len(sets)==2
    successor,record=next(j.joint_stage_successors(st.values,p,widths=(3,)))
    ops,out=j.reconstruct_joint_frame(st.values,record)
    assert out==successor and i.full_step(i.INITIAL,st.ops+ops)==successor


def test_first_semantic_completion_is_reconstructed_and_verified(tmp_path):
    controls=(3,6,12,24,48,32)
    funcs=[i.restrict_clean(i.evaluate_mask(i.INITIAL,m)) for m in controls]
    products=tuple((funcs[r],funcs[r+1],funcs[r]&funcs[r+1]) for r in (0,2,4))
    goals=tuple(g for _,_,g in products)+(s.INPUTS[5],)
    initial=[i.State(i.INITIAL,(0,)*9,())]
    result=j.search(initial,products,goals,tmp_path,stages=1,seconds=5,widths=(3,),burst=64)
    assert result['status']=='semantic_complete'
    assert result['encoder']['checked_inputs']==64
    assert len(result['encoder']['outputs'])==4
    assert (tmp_path/'completion.json').exists() and (tmp_path/'encoder.qasm').exists()


def test_relaxed_bound_for_y_prefix_and_synthetic_stage():
    w=json.loads(Path('artifacts/post190_nist_variants_wide/y_candidate_0.json').read_text());products,goals=s.bank(w,'y')
    st=i.restore(json.loads(Path('artifacts/post190_information_space/comparison_cached/B/frontier.json').read_text())[0])
    assert j.relaxed_stage_bound(i.canonical(st.clean,s.FULL),products,goals)==3
    # Unlimited storage contains every actual joint successor, stage by stage.
    p=s.pivots((s.FULL,*st.clean));relaxed=(*st.clean,*(g for a,b,g in products if s.contains(p,a) and s.contains(p,b)))
    rp=s.pivots((s.FULL,*relaxed))
    for out,_ in itertools.islice(j.joint_stage_successors(st.values,products),100):
        assert all(s.contains(rp,i.restrict_clean(v)) for v in out)
