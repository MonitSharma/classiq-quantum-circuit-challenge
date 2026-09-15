import sys
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from post185_sat_phase_blocks import solve
from distributed_frame_search import native


def test_parallel_phases_are_counted_with_cnot_layers():
    q = QuantumCircuit(5)
    q.cx(0, 1)
    q.cx(2, 3)
    q.p(.123, 4)
    candidate, info = solve(native(q), 1, seconds=3)
    assert info['status'] == 'sat'
    assert candidate.depth() == 1
    assert Operator(q).equiv(Operator(candidate), atol=1e-10, rtol=0)


def test_parity_rotation_cannot_be_done_in_one_native_layer():
    q = QuantumCircuit(5)
    q.cx(0, 1)
    q.p(.123, 1)
    q.cx(0, 1)
    candidate, info = solve(native(q), 1, seconds=3)
    assert candidate is None and info['status'] == 'unsat'
    candidate, info = solve(native(q), 3, seconds=3)
    assert candidate is not None
    assert Operator(q).equiv(Operator(candidate), atol=1e-10, rtol=0)


def test_arbitrary_dirty_spectators_and_deadlines():
    q = QuantumCircuit(6)
    q.cx(0, 5)
    q.p(.312, 5)
    # Release both active wires at t=2 and finish by t=4.
    candidate, info = solve(native(q), 4, seconds=3,
                            arrivals=[2, 0, 0, 0, 0, 2], deadlines=[4] * 6)
    assert candidate is not None
    for layer in info['layers'][:2]:
        for gate in layer:
            wires = gate[1:] if gate[0] == 'cx' else gate[1:2]
            assert not {0, 5}.intersection(wires)
    assert Operator(q).equiv(Operator(candidate), atol=1e-10, rtol=0)
