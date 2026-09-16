import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator
from destructive_phase_xag import State, apply, basis, represent, clock_ops, emit, replay
from destructive_xag import load_xag, ParsedXAG
from md_xag import AndNode, input_truth_tables
from post129_phase_rooted_xag import resume_state
from post185_selective_recovery import inverse_cone, orient_native, SelectiveRecovery, save_trace


def test_inverse_cone_restores_requested_output_and_retains_unrelated_work():
    initial=tuple(input_truth_tables())+(0,)*6
    compute=[('ccx',[0,1,2]),('cx',[2,3]),('ccx',[3,4,0])]
    rows=apply(initial,compute)
    sliced=inverse_cone(compute,[2])
    assert len(sliced)==2
    final=apply(rows,sliced)
    assert final[2]==initial[2] and final[3]!=initial[3]


def test_real_checkpoint_recovers_input_in_two_ccx_and_four_added_layers():
    parsed=load_xag(Path('artifacts/multiplicative_depth/optimized/advanced_round4.xag'))
    lower=SelectiveRecovery(parsed)
    state=resume_state(lower,Path('artifacts/post129_phase_rooted_longer/best.json'))
    sliced=inverse_cone(state.ops,[8])
    assert sliced==[('ccx',[6,7,17]),('ccx',[9,17,8])]
    assert apply(state.rows,sliced)[8]==lower.initial[8]
    assert max(clock_ops(state.clocks,sliced))==44


def assert_small_quantum_phase(state,initial):
    q=qasm2.loads(qasm2.dumps(emit(state,18)))
    used=sorted({q.find_bit(w).index for inst in q.data for w in inst.qubits})
    assert len(used)<=8
    small=QuantumCircuit(len(used))
    for inst in q.data:small.append(inst.operation,[used.index(q.find_bit(w).index) for w in inst.qubits])
    u=Operator(small).data;global_phase=None
    for x in range(1<<len(used)):
        if any((x>>i)&1 for i,w in enumerate(used) if w>=12):continue
        original=sum(((x>>i)&1)<<w for i,w in enumerate(used))
        sign=(-1)**((state.phase>>original)&1)
        if global_phase is None:global_phase=u[x,x]/sign
        expected=np.zeros(len(u),complex);expected[x]=global_phase*sign
        assert np.allclose(u[:,x],expected,atol=1e-12)
    assert replay(state,initial,state.phase)


def test_semantic_release_uses_changed_frame_and_preserves_deposited_phase():
    parsed=ParsedXAG((AndNode(2,4),),1<<13)
    lower=SelectiveRecovery(parsed)
    ops=(('ccx',[0,1,12]),('z',[12]),('cx',[2,0]))
    state=State(apply(lower.initial,ops),1,lower.signals[13],1,ops,clock_ops((0,)*18,ops),())
    released=lower.release_proposals(state)
    assert released
    best=min(released,key=lambda s:max(s.clocks))
    assert best.rows[best.history[-1]['target']]==0
    assert_small_quantum_phase(best,lower.initial)


def test_one_and_algebraic_recovery_is_reversible_and_exact():
    # x2 is missing after a dirty AND. Root demand needs original x2.
    parsed=ParsedXAG((AndNode(2,4),AndNode(1<<3,1<<4)),1<<14)
    lower=SelectiveRecovery(parsed)
    ops=(('ccx',[0,1,2]),)
    state=State(apply(lower.initial,ops),1,0,0,ops,clock_ops((0,)*18,ops),())
    assert represent(basis(state.rows),lower.signals[3]) is None
    choices=lower.algebraic_recovery(state)
    assert choices
    best=min(choices,key=lambda s:max(s.clocks))
    assert represent(basis(best.rows),lower.signals[3]) is not None
    assert_small_quantum_phase(best,lower.initial)


def test_trace_semantic_phase_is_replayed_not_assumed(tmp_path):
    parsed=ParsedXAG((AndNode(2,4),),1<<13)
    lower=SelectiveRecovery(parsed)
    state=lower.initial_state();path=tmp_path/'state.json'
    save_trace(path,state,{})
    restored=resume_state(lower,path)
    assert restored.phase==state.phase
    data=json.loads(path.read_text());data['semantic_phase_hex']='0x1';path.write_text(json.dumps(data))
    import pytest
    with pytest.raises(AssertionError):resume_state(lower,path)


def test_orientation_uses_primitive_arrivals_and_literal_inverse_is_exact():
    clocks=(0,10,0)+(0,)*15
    ops=[('ccx',[0,1,2]),('z',[2])]
    oriented,end=orient_native(ops,clocks)
    assert max(end)<max(clock_ops(clocks,ops))
    initial=tuple(input_truth_tables())+(0,)*6;rows=apply(initial,oriented)
    state=State(rows,0,rows[2],0,tuple(oriented),clock_ops((0,)*18,oriented),())
    assert_small_quantum_phase(state,initial)


def test_affine_destination_computes_consumer_without_a_clean_target():
    parsed=ParsedXAG((AndNode(2,4),AndNode((1<<3)|(1<<4)|(1<<13),1<<5)),1<<14)
    lower=SelectiveRecovery(parsed,target_forms=True)
    candidates=lower.target_form_proposals(lower.initial_state())
    best=next(s for s in candidates if any(h.get('target_operand') and h['target']==2 for h in s.history))
    assert best.phase==lower.target
    assert all(w<12 for _,ws in best.ops for w in ws)
    assert_small_quantum_phase(best,lower.initial)


def test_native_cap_includes_phase_deposition_after_recovery():
    parsed=ParsedXAG((AndNode(2,4),AndNode((1<<3)|(1<<4)|(1<<13),1<<5)),1<<14)
    lower=SelectiveRecovery(parsed,max_forward=7,orient=True,target_forms=True)
    candidates=lower.successors(lower.initial_state())
    assert all(max(s.clocks)<=7 for s in candidates)
