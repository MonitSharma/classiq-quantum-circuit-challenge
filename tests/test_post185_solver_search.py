import pytest
pytest.importorskip('ortools')
from qiskit import QuantumCircuit
from qiskit.circuit.library import U3Gate
from qiskit.quantum_info import Operator
from post185_solver_walk import bounded_schedule
from post185_phase_placement import optimize, problem


def test_schedule_ceiling_distinguishes_feasible_and_impossible():
    q=QuantumCircuit(3)
    q.cx(0,1)
    q.cx(1,2)
    good,report=bounded_schedule(q,2,3,0)
    assert good is not None and Operator(good).equiv(Operator(q))
    bad,report=bounded_schedule(q,1,3,0)
    assert bad is None


@pytest.mark.parametrize('commuting',[False,True])
def test_phase_placement_preserves_entire_unitary_across_hadamard_fences(commuting):
    q=QuantumCircuit(3)
    q.cx(0,1)
    q.append(U3Gate(0,0,.3),[1])
    q.cx(0,1)
    q.cx(1,2)
    q.append(U3Gate(0,0,.7),[2])
    q.append(U3Gate(.4,.1,-.2),[0])
    q.cx(0,2)
    q.append(U3Gate(0,0,-.9),[2])
    q.cx(0,2)
    q.append(U3Gate(0,0,.2),[2])
    result,report=optimize(q,5,q.depth(),commuting)
    assert result is not None,report
    assert Operator(q).equiv(Operator(result),atol=1e-11,rtol=0)


def test_repeated_parity_rotations_merge_in_placement_model():
    q=QuantumCircuit(3)
    q.cx(0,1)
    q.append(U3Gate(0,0,.3),[1])
    q.cx(0,1)
    q.cx(0,1)
    q.append(U3Gate(0,0,.2),[1])
    fixed,phases=problem(q)
    assert len(phases)==1 and len(phases[0]['options'])>=2
    result,report=optimize(q,5,q.depth())
    assert result is not None and Operator(q).equiv(Operator(result),atol=1e-11,rtol=0)


def test_commuting_target_cnots_do_not_invalidate_phase_occurrence():
    q=QuantumCircuit(4)
    for a in (0,1,2,0,2,1):
        q.cx(a,3)
        q.append(U3Gate(0,0,.13*(a+1)),[3])
        q.append(U3Gate(0,0,.19),[a])
    result,report=optimize(q,5,q.depth(),True)
    assert result is not None,report
    assert Operator(q).equiv(Operator(result),atol=1e-11,rtol=0)
