import numpy as np
from pathlib import Path
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator
from destructive_xag import load_xag, ParsedXAG
from md_xag import AndNode
from destructive_phase_xag import clock_ops, replay, emit
from post129_phase_rooted_xag import PhaseRooted, resume_state
from phase_rooted_frames import coefficients, expose, build, root_witnesses, emit_paired


def small_graph():
    return ParsedXAG((AndNode(2,4),AndNode((1<<3)|(1<<13)|1,1<<4)),(1<<13)|(1<<14))


def assert_clean_oracle(q, target):
    used=sorted({q.find_bit(w).index for inst in q.data for w in inst.qubits})
    assert len(used)<=8
    small=QuantumCircuit(len(used))
    for inst in q.data:small.append(inst.operation,[used.index(q.find_bit(w).index) for w in inst.qubits])
    u=Operator(small).data;phase=None
    for x in range(1<<len(used)):
        if any(x>>i&1 for i,w in enumerate(used) if w>=12):continue
        original=sum(((x>>i)&1)<<w for i,w in enumerate(used))
        expected=np.zeros(len(u),complex);expected[x]=(-1)**((target>>original)&1)
        if phase is None:phase=u[x,x]/expected[x]
        assert np.allclose(u[:,x],phase*expected,atol=1e-12)


def test_inventory_and_backward_demand():
    p=load_xag(Path('artifacts/multiplicative_depth/optimized/advanced_round4.xag'))
    lower=PhaseRooted(p);s=lower.initial_state()
    assert len(p.nodes)==62 and len(lower.roots)==11 and len(lower.terminal)==9
    missing,lost,_=lower.demand(s,54)
    assert len(missing)==5 and not lost and 54 not in missing
    assert not missing&lower.terminal


def test_nonterminal_root_can_be_phased_without_materialization():
    lower=PhaseRooted(small_graph());s=lower.phase_ready(lower.initial_state())
    assert s.phased_roots&1 and not s.done&1
    assert any(name=='cz' for name,_ in s.ops)
    assert not replay(s,lower.initial,lower.target)


def test_destructive_rooted_search_completes_and_cancels_relative_phases():
    lower=PhaseRooted(small_graph());s,r=lower.run_rooted(seconds=5,beam=4)
    assert replay(s,lower.initial,lower.target)
    assert_clean_oracle(qasm2.loads(qasm2.dumps(emit(s,18))),lower.target)


def test_formal_exposures_preserve_affine_constants():
    rows=(2,4,8,0,0)
    options=expose(rows,2^8^1,4^8,(0,)*5,20)
    assert options and coefficients(rows,2^4^1) is not None
    for _,_,_,a,b,framed,_ in options:
        assert framed[a]==2^8^1 and framed[b]==4^8


def test_retained_frames_have_exact_timing_and_paired_quantum_phases():
    p=small_graph();ops,r=build(p,root_witnesses(p),seed=1)
    q=qasm2.loads(qasm2.dumps(emit_paired(ops)))
    assert q.depth()==r['depth']==max(clock_ops((0,)*18,ops))
    assert_clean_oracle(q,p.graph.evaluate())


def test_saved_phase_trajectory_resumes_with_checked_truth_tables(tmp_path):
    import json
    lower=PhaseRooted(small_graph(),suffix_recovery=True)
    s=lower.phase_ready(lower.initial_state())
    path=tmp_path/'trace.json'
    path.write_text(json.dumps(dict(ops=s.ops,phase_mask=s.phased_roots,history=s.history)))
    restored=resume_state(lower,path)
    assert restored.rows==s.rows and restored.phase==s.phase and restored.clocks==s.clocks
    complete,_=lower.run_rooted(seconds=5,initial=restored)
    assert replay(complete,lower.initial,lower.target)
    assert_clean_oracle(qasm2.loads(qasm2.dumps(emit(complete,18))),lower.target)
