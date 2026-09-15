import json,random
from pathlib import Path
import post190_information_space as i
import post190_semantic_register as s


def test_full_extensions_and_projection():
    assert len(i.affine_span(i.INITIAL))==1024
    assert tuple(map(i.restrict_clean,i.INITIAL))==s.INPUTS+(0,0,0)
    aliases=i.affine_preimages_of_clean_function(i.INITIAL,s.INPUTS[0])
    assert len(aliases)==8 and len({t for t,m in aliases})==8
    assert all(i.restrict_clean(t)==s.INPUTS[0] for t,m in aliases)


def test_off_manifold_is_not_extra_clean_information():
    ops=(('cx',(6,0)),('ccx',(0,1,2)))
    assert i.restrict_clean(i.full_step(i.INITIAL,ops)[2])==s.step(s.INPUTS+(0,0,0),ops)[2]


def test_frame_synthesis_random_invertible():
    rng=random.Random(12)
    for _ in range(6):
        ops=[('cx',tuple(rng.sample(range(9),2))) for j in range(25)]+[('x',(2,))]
        new=i.full_step(i.INITIAL,ops)
        q,d,c=i.synthesize_affine_frame(i.INITIAL,new)
        assert d==q.depth() and c==q.count_ops().get('cx',0)
        # Verify actual native circuit on every full input, ignoring RCCX-free phase.
        from qiskit.quantum_info import Statevector
        import numpy as np
        for x in range(512):
            want=sum(((t>>x)&1)<<j for j,t in enumerate(new))
            state=Statevector.from_int(x,512).evolve(q).data
            assert abs(state[want]-1)<1e-10


def test_dominance_keeps_incomparable_timing_and_basis():
    dom=i.Dominance('pareto')
    assert dom.accept(i.State(i.INITIAL,(8,0,0,0,0,0,0,0,0),()))
    assert dom.accept(i.State(i.INITIAL,(0,8,0,0,0,0,0,0,0),()))
    assert not dom.accept(i.State(i.INITIAL,(8,8,0,0,0,0,0,0,0),()))
    assert dom.accept(i.State(i.full_step(i.INITIAL,[('cx',(0,1))]),(8,)*9,()))


def test_span_collision_concrete_cheaper_goal():
    v=s.INPUTS+(0,0,0);changed=s.step(v,[('cx',(0,1))])
    assert s.span_key(v)==s.span_key(changed)
    assert max(s.finish(v,(0,)*9,(s.INPUTS[1],))[2])==0
    assert max(s.finish(changed,(0,)*9,(s.INPUTS[1],))[2])==1


def test_rank_deficit_sees_goal_combinations():
    g0=s.INPUTS[0]&s.INPUTS[1];g1=s.INPUTS[2]&s.INPUTS[3]
    clean=(*s.INPUTS,g0^g1,0,0)
    m=i.state_metrics(clean,(),(g0,g1))
    assert m['present']==[] and m['rank_deficit']==1


def test_snapshot_and_packed_stages():
    ops=(('ccx',(0,1,6)),('ccx',(2,3,7)),('ccx',(4,5,8)))
    state=i.State(i.full_step(i.INITIAL,ops),s.timing((0,)*9,ops),ops,1)
    data=i.snapshot(state,(),(s.INPUTS[0],))
    assert i.restore(data)==state and i.nonlinear_depth(ops)==1
    assert s.compile_ops(ops).depth()==7


def test_search_positive_control():
    w={'k':1,'gates':[{'a':([0],False),'b':([1],False)}], 'outs':[([2,6],False),([3],False),([4],False)]}
    report,best,partials=i.search(w,'y',seconds=6,beam=24,steps=3,aliases=1,exposure_limit=2)
    assert best and best['report']['checked_inputs']==64
    assert best['report']['depth']<20


def test_semantic_hyperplane_transitions_replay_exactly():
    from post190_information_quotient import transitions
    w=json.loads(Path('artifacts/post190_nist_variants_wide/y_candidate_0.json').read_text())
    products,goals=s.bank(w,'y');state=i.State(i.INITIAL,(0,)*9,())
    count=0
    for key,out,tail,gate in transitions(state,products,goals,aliases=1):
        assert i.full_step(state.values,tail)==out
        assert key==i.canonical(tuple(map(i.restrict_clean,out)),s.FULL)
        assert len(s.pivots((i.ALL,*out)))==10
        count+=1
        if count==100:break
    assert count>5


def test_completion_on_last_allowed_stage_is_not_lost():
    w={'k':1,'gates':[{'a':([0],False),'b':([1],False)}], 'outs':[([2,6],False),([3],False),([4],False)]}
    report,best,_=i.search(w,'y',seconds=6,beam=8,steps=1,aliases=1,exposure_limit=2)
    assert best and report['status']=='complete'
