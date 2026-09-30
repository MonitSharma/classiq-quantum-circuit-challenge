"""Check arbitrary-angle operator identities, not only classical output labels."""
import sys
from pathlib import Path
import numpy as np
import pytest
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from distributed_ucry import structured_ucry, verify_component
from distributed_frame_search import native, factored_base_kernel


@pytest.mark.parametrize('sparse,open_walk', [(False, False), (False, True), (True, False)])
def test_arbitrary_angle_lookups(sparse, open_walk):
    rng = np.random.default_rng(712)
    tables = rng.uniform(-2*np.pi, 2*np.pi, (3, 64))
    # Deliberately include exact zero angles; the full operator must still agree.
    tables[:, ::3] = 0
    q = native(structured_ucry(tables, [6, 7, 8], list(range(6)), seed=11,
                               sparse=sparse, open_walk=open_walk))
    assert verify_component(q, tables) < 1e-10


def expected_kernel():
    values = []
    for z in range(64):
        a, b, c, d, e, f = [(z >> i) & 1 for i in range(6)]
        exponent = (a*f) ^ (a*b*d) ^ (a*c*e) ^ (b*d*f) ^ (c*e*f)
        values.append((-1)**exponent)
    return np.diag(values)


@pytest.mark.parametrize('optimized', [False, True])
def test_kernel_all_basis_states(optimized):
    if optimized:
        path = Path(__file__).resolve().parents[1] / 'artifacts/distributed_kernel_lifted/kernel_d13_cx15.qasm'
        q = qasm2.load(path)
    else:
        q = native(factored_base_kernel())
    op = Operator(q).data
    want = expected_kernel()
    phase = np.vdot(want, op)
    assert np.max(np.abs(op-phase/abs(phase)*want)) < 1e-10
