import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import U3Gate
from qiskit.quantum_info import Operator

from post186_exact_local_phase import collect, extract, replace, synthesize
from post190_commuting_schedule import records


def test_exact_resynthesis_cancels_repeated_parity_and_preserves_output_map():
    q = QuantumCircuit(3)
    q.cx(0, 1)
    q.append(U3Gate(0, 0, .37), [1])
    q.cx(0, 1)
    q.cx(0, 1)
    q.append(U3Gate(0, 0, -.37), [1])
    q.cx(1, 2)
    result = synthesize(q)
    assert result.depth() < q.depth()
    assert Operator(q).equiv(Operator(result), atol=1e-12, rtol=0)


@pytest.mark.parametrize('width', [3, 4])
def test_convex_region_respects_external_interactions_and_hadamards(width):
    rng = np.random.default_rng(186)
    for _ in range(12):
        q = QuantumCircuit(5)
        q.cx(0, 1)
        for _ in range(30):
            a, b = rng.choice(5, 2, replace=False)
            if rng.random() < .65:
                q.cx(int(a), int(b))
            else:
                theta = 0 if rng.random() < .8 else np.pi/2
                q.append(U3Gate(theta, 0, .13), [int(a)])
        wires = tuple(range(width))
        selected = collect(records(q), 0, wires)
        local = extract(q, selected, wires)
        if width == 3:
            replacement = synthesize(local)
        else:
            from post190_window_phase import polynomial, finish_to
            from post218_beam_phase import psynth
            targets, goal, phase = polynomial(local)
            def finish(body, basis):
                out = finish_to(body, basis, goal)
                return (out.depth(), len(out.data)), out
            replacement = psynth(width, targets, global_phase=phase, finalize=finish, max_steps=128)
        result = replace(q, selected, replacement, wires)
        assert Operator(q).equiv(Operator(result), atol=1e-11, rtol=0)
