import math
import random
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from destructive_phase_xag import Lowerer,State,apply,basis,represent,exposures,emit,replay,clock_ops
from destructive_xag import ParsedXAG
from md_xag import AndNode,FULL,input_truth_tables


def test_reversible_coordinate_overwrite_need_not_preserve_affine_input_span():
    rows=tuple(input_truth_tables())+(0,)*6
    changed=apply(rows,[('ccx',[0,1,2])])
    assert represent(basis(changed),rows[2]) is None
    assert apply(changed,[('ccx',[0,1,2])])==rows


def test_control_materialization_retains_correct_affine_constants():
    rows=tuple(input_truth_tables())+(0,)*6
    left=rows[0]^rows[2]^FULL;right=rows[0]^rows[1]^rows[2]
    options=exposures(rows,left,right,(0,)*18,20)
    assert options
    for _,_,ops,a,b,framed,_ in options:
        assert framed[a]==left and framed[b]==right
        assert apply(framed,list(reversed(ops)))==rows


def test_known_dag_lowers_with_no_clean_ancillas_using_dirty_coordinates():
    # n0=x0*x1; root=(x2 XOR n0)*x3. Dirty x2 is the desired next control.
    parsed=ParsedXAG((AndNode(2,4),AndNode((1<<3)|(1<<13),1<<4)),1<<14)
    lower=Lowerer(parsed,width=12)
    state,report=lower.run(seconds=3,beam=6)
    assert report['status']=='exact'
    assert replay(state,lower.initial,lower.target)
    assert any(h.get('dirty') and h.get('target',12)<12 for h in state.history)
    assert any(h.get('phase_only') for h in state.history)
    q=qasm2.loads(qasm2.dumps(emit(state,12)))
    used=sorted({q.find_bit(w).index for inst in q.data for w in inst.qubits})
    small=QuantumCircuit(len(used))
    for inst in q.data:small.append(inst.operation,[used.index(q.find_bit(w).index) for w in inst.qubits])
    signs=[]
    for point in range(1<<len(used)):
        original=sum(((point>>i)&1)<<w for i,w in enumerate(used))
        signs.append((-1)**((lower.target>>original)&1))
    u=Operator(small).data
    assert np.allclose(u,np.diag(signs),atol=1e-13)
    assert max(state.clocks)<=q.depth()


def test_intermediate_phase_taps_cancel_relative_phases_with_literal_inverse():
    initial=tuple(input_truth_tables())+(0,)*6
    ops=(('ccx',[0,1,2]),('z',[2]),('cx',[2,3]),('ccx',[3,4,0]),('cz',[0,1]))
    rows=initial;phase=0
    for kind,ws in ops:
        if kind=='z':phase^=rows[ws[0]]
        elif kind=='cz':phase^=rows[ws[0]]&rows[ws[1]]
        else:rows=apply(rows,[(kind,ws)])
    state=State(rows,0,phase,0,ops,clock_ops((0,)*18,ops),())
    assert replay(state,initial,phase)
    q=qasm2.loads(qasm2.dumps(emit(state,18)));small=QuantumCircuit(5)
    for inst in q.data:small.append(inst.operation,[q.find_bit(w).index for w in inst.qubits])
    assert np.allclose(Operator(small).data,np.diag([(-1)**((phase>>x)&1) for x in range(32)]),atol=1e-13)
