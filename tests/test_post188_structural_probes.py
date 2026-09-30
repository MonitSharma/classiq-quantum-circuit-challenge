import numpy as np
import pytest
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator

from post188_joint_phase_loader import (SCALE, lift_moves, starting_coefficients,
                                        values_for, verify_phase)
from post188_phasepoly_probe import phasepoly_input
from post186_split_schedule import split_native


def test_joint_lifts_preserve_code_for_every_address_and_target():
    moves, _ = lift_moves()
    rng = np.random.default_rng(188)
    for side in ['x', 'y']:
        values = values_for(side)
        co = starting_coefficients(values)
        assert verify_phase(co, values) < 1e-10
        for i in rng.choice(len(moves), 24, replace=False):
            co = (co + moves[i]) % SCALE
            assert verify_phase(co, values) < 1e-10
        bad = co.copy()
        bad[64] = (bad[64] + 1) % SCALE
        with pytest.raises(AssertionError):
            verify_phase(bad, values)


def test_phasepoly_conversion_preserves_full_unitary():
    from qiskit.circuit.library import U3Gate
    q = QuantumCircuit(3)
    for index, theta in enumerate([0., np.pi/2, -np.pi/2, np.pi*.75, np.pi*2/3, .123]):
        j = index % 3
        q.append(U3Gate(theta, np.pi/16, -np.pi/8), [j])
        q.cx(j, (j+1) % 3)
    actual = qasm2.loads(phasepoly_input(q))
    assert Operator(q).equiv(Operator(actual), atol=1e-12, rtol=0)
    assert set(actual.count_ops()) <= {'h', 'rz', 'cx'}
    split = qasm2.loads(qasm2.dumps(split_native(q)))
    assert Operator(q).equiv(Operator(split), atol=1e-12, rtol=0)
    assert set(split.count_ops()) <= {'u3', 'cx'}
