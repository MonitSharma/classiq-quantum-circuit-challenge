"""The beam phase scheduler must emit every requested parity, exactly."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from qiskit import qasm2
from qiskit.quantum_info import Operator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from depth_parity_network import walsh          # noqa: E402
from post218_beam_phase import psynth           # noqa: E402


def _diagonal_error(circuit, phases):
    op = Operator(qasm2.loads(qasm2.dumps(circuit))).data
    want = np.diag(np.exp(1j * phases))
    overlap = np.vdot(want, op)
    return float(np.max(abs(op - overlap / abs(overlap) * want)))


@pytest.mark.parametrize('n,seed', [(4, 0), (4, 3), (5, 1), (6, 2)])
def test_random_phase_polynomial_is_exact(n, seed):
    rng = np.random.default_rng(seed)
    phases = rng.normal(size=1 << n)
    co = walsh(phases)
    targets = {m: float(co[m]) for m in range(1, 1 << n) if abs(co[m]) > 1e-12}
    q = psynth(n, targets, seed=seed, beam=8, branch=5, global_phase=float(co[0]))
    assert _diagonal_error(q, phases) < 1e-10


def test_every_requested_parity_is_emitted_once():
    """Guards the bug where an incomplete beam state was returned as a schedule."""
    rng = np.random.default_rng(7)
    n = 5
    phases = rng.normal(size=1 << n)
    co = walsh(phases)
    targets = {m: float(co[m]) for m in range(1, 1 << n) if abs(co[m]) > 1e-12}
    q = psynth(n, targets, seed=4, beam=6, branch=4, global_phase=float(co[0]))
    basis = [1 << w for w in range(n)]
    seen = []
    for inst in q.data:
        wires = [q.find_bit(b).index for b in inst.qubits]
        if inst.operation.name == 'cx':
            basis[wires[1]] ^= basis[wires[0]]
        elif inst.operation.name == 'rz':
            seen.append(basis[wires[0]])
    assert sorted(seen) == sorted(targets)
    assert basis == [1 << w for w in range(n)], 'linear state not restored'


def test_matches_the_verified_196_kernel_spectrum():
    import json
    recipe = json.loads(Path('artifacts/218/kernel_recipe.json').read_text())
    phases = walsh(np.array(recipe['co'], float) / 32) * 256 * math.pi
    co = walsh(phases)
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    assert len(targets) == 69
    q = psynth(8, targets, seed=209, beam=64, branch=14, alpha=5.0, timew=0.35,
               global_phase=float(co[0]))
    assert _diagonal_error(q, phases) < 1e-10
