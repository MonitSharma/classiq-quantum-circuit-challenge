import itertools
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from post186_cnot_bridge import rewrite


def test_bridge_identities_in_both_directions_with_interleaved_gates():
    for a, b, c in itertools.permutations(range(3)):
        for first, second in [((a, b), (b, c)), ((b, c), (a, b))]:
            for direction in ['left', 'right']:
                q = QuantumCircuit(4)
                q.cx(*first)
                q.rz(.31, 3)
                q.cx(*second)
                assert Operator(q).equiv(Operator(rewrite(q, 0, 2, direction)), atol=1e-12, rtol=0)
