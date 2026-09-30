import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from post190_commuting_schedule import commute, dependency_graph, reordered, schedule


def test_commutation_predicates_against_small_operators():
    gates = []
    for a in range(3):
        for b in range(3):
            if a != b:
                gates.append(('cx', (a, b), ()))
        for params in [(0., 0., .31), (.4, -.5, .2), (.37, -np.pi/2, np.pi/2),
                       (np.pi/2, 0., np.pi)]:
            gates.append(('u3', (a,), params))
    def operator(seq):
        q = QuantumCircuit(3)
        for name, w, p in seq:
            if name == 'cx': q.cx(*w)
            else: q.u(*p, w[0])
        return Operator(q).data
    for a in gates:
        for b in gates:
            if commute(a, b):
                assert np.max(abs(operator([a, b])-operator([b, a]))) < 1e-12


def test_schedules_preserve_full_operator():
    q = QuantumCircuit(4)
    q.h(0)
    q.cx(0, 1)
    q.rz(.27, 0)
    q.cx(0, 2)
    q.cx(3, 2)
    q.rx(.51, 2)
    q.cx(1, 3)
    q.h(1)
    from distributed_frame_search import native
    q = native(q)
    ops, succ, pred = dependency_graph(q)
    for seed in range(24):
        out = reordered(q, schedule(ops, succ, pred, seed), pred)
        assert np.max(abs(Operator(out).data-Operator(q).data)) < 1e-12
