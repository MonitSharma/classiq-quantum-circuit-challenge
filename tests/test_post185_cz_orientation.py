import random
import sys
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from distributed_frame_search import native
from post185_cz_orientation import to_cz, lower, prepared, graph
from post190_commuting_schedule import reordered, schedule


def sample():
    rng = random.Random(30)
    q = QuantumCircuit(5, global_phase=.73)
    for _ in range(30):
        a, b = rng.sample(range(5), 2)
        q.cx(a, b)
        q.u(rng.random(), rng.random(), rng.random(), b)
    return native(q)


def test_both_cnot_orientations_preserve_arbitrary_inputs_and_phase():
    original = sample()
    cz, _ = to_cz(original)
    assert Operator(original).equiv(Operator(cz), atol=1e-10, rtol=0)
    rng = random.Random(3)
    for _ in range(4):
        choices = [rng.randrange(2) for _ in range(cz.count_ops()['cz'])]
        score, q = lower(cz, prepared(cz), choices, emit=True)
        assert score[0] == q.depth()
        assert Operator(original).equiv(Operator(q), atol=1e-10, rtol=0)


def test_cz_commutation_graph_reordering_keeps_operator():
    original = sample()
    cz, _ = to_cz(original)
    ops, succ, pred = graph(cz)
    for seed in range(3):
        q = reordered(cz, schedule(ops, succ, pred, seed), pred)
        assert Operator(original).equiv(Operator(q), atol=1e-10, rtol=0)


def test_joint_orientation_depth_matches_brute_force():
    import itertools
    import pytest
    pytest.importorskip('ortools')
    from post185_cz_orientation import exact_orientations
    q = QuantumCircuit(3)
    q.h(1)
    q.cx(0, 1)
    q.cx(2, 1)
    q.p(.2, 1)
    q.cx(0, 2)
    cz, _ = to_cz(native(q))
    ops = prepared(cz)
    expected = min(lower(cz, ops, choices)[0][0]
                   for choices in itertools.product((0, 1), repeat=cz.count_ops()['cz']))
    result, info = exact_orientations(cz, seconds=3)
    assert info['status'] == 'OPTIMAL'
    assert result.depth() == expected
    assert Operator(q).equiv(Operator(result), atol=1e-10, rtol=0)
