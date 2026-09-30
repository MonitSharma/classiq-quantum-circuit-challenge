import itertools
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from post185_mediated_cx import mediated
from post185_depth_walk import profile
from post185_relabel_compile import compile_permuted
from post185_timed_local import solve_window


def test_dirty_mediator_restores_arbitrary_helper():
    for a, b, k in itertools.permutations(range(3)):
        q = QuantumCircuit(3)
        q.h(k)
        q.rz(.21, a)
        q.cx(a, b)
        q.rx(.33, k)
        for reverse in (False, True):
            result = mediated(q, 2, k, reverse)
            assert Operator(q).equiv(Operator(result), atol=1e-12, rtol=0)


def test_critical_profile_excludes_idle_short_branch():
    q = QuantumCircuit(4)
    q.h(0)
    q.cx(0, 1)
    q.cx(1, 2)
    q.h(3)
    depth, critical = profile(q)
    assert depth == q.depth() == 3
    assert critical == {0, 1, 2}


def test_relabelled_compilation_preserves_full_unitary_and_inverse():
    q = QuantumCircuit(4)
    q.h(0)
    q.cx(0, 2)
    q.rz(.19, 1)
    q.swap(2, 3)
    q.cx(1, 3)
    q.ry(.37, 2)
    for inverse in (False, True):
        result = compile_permuted(q, [3, 1, 0, 2], 8, inverse)
        assert Operator(q.inverse() if inverse else q).equiv(Operator(result), atol=1e-11, rtol=0)


def test_timed_window_honors_late_input_and_early_output_deadlines():
    q = QuantumCircuit(3)
    q.cx(0,1)
    q.rz(.3,1)
    q.cx(0,1)
    # Convert Rz to native phase; local solver ignores only shared global phase.
    from distributed_frame_search import native
    q = native(q)
    result, report = solve_window(q,[2,0,0],[0,1,0],6)
    assert report['status']=='found'
    assert Operator(q).equiv(Operator(result),atol=1e-11,rtol=0)
    from post258_joint_encoder_schedule import touches
    assert max(t+d for t,d in zip(touches(result,[2,0,0]),[0,1,0]))<=6
    result, report = solve_window(q,[2,0,0],[0,1,0],3)
    assert result is None and report['status']=='infeasible_in_local_model'


def test_timed_four_wire_search_can_place_two_cnots_in_one_layer():
    q = QuantumCircuit(4)
    q.cx(0,1)
    q.cx(2,3)
    result, report = solve_window(q,[0]*4,[0]*4,1)
    assert report['status']=='found' and result.depth()==1
    assert Operator(q).equiv(Operator(result),atol=1e-12,rtol=0)
