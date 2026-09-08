"""Quantum emitter for an exact mixed-support LUT decomposition model."""

import random

import numpy as np
from qiskit import QuantumCircuit, transpile

from mcz import phase_cube
from search import esop


def _ucry(table, controls, target, order):
    """Synthesize one Boolean LUT as a Walsh/Gray uniformly controlled RY."""
    n = len(controls)
    size = 1 << n
    angles = np.array([
        np.pi * ((table >> sum(((assignment >> j) & 1) << v
                                for j, v in enumerate(order))) & 1)
        for assignment in range(size)
    ], dtype=float)
    h = 1
    while h < size:
        for start in range(0, size, 2 * h):
            lo = angles[start:start + h].copy()
            hi = angles[start + h:start + 2 * h].copy()
            angles[start:start + h] = lo + hi
            angles[start + h:start + 2 * h] = lo - hi
        h *= 2
    angles /= size
    q = QuantumCircuit(18)
    for j in range(size):
        angle = float(angles[j ^ (j >> 1)])
        if abs(angle) > 1e-14:
            q.ry(angle, target)
        position = ((j + 1) & -(j + 1)).bit_length() - 1 \
            if j < size - 1 else n - 1
        q.cx(controls[order[position]], target)
    return q


def multiplexer_general(tables, supports, outputs, seed=0):
    """Load arbitrary <=6-input LUTs into distinct clean output wires."""
    assert len(tables) == len(supports) == len(outputs)
    rng = random.Random(seed)
    q = QuantumCircuit(18)
    for table, support, target in zip(tables, supports, outputs):
        controls = list(support)
        order = list(range(len(controls)))
        rng.shuffle(order)
        q.compose(_ucry(table, controls, target, order), inplace=True)
    return q


def phase_upper(q, gmask, nfeatures, outputs):
    """Apply G(feature bits) as an exact XOR-of-cubes diagonal phase."""
    for mask, value in esop(gmask, nfeatures):
        cube = [outputs[bit] + 1 if value >> bit & 1
                else -(outputs[bit] + 1)
                for bit in range(nfeatures) if mask >> bit & 1]
        phase_cube(q, frozenset(cube), [])


def build(model, seed=0):
    """Emit and score a model returned by lut_decomposition."""
    supports = [tuple(s) for s in model['supports']]
    tables = model['tables']
    nfeatures = len(tables)
    outputs = list(range(12, 12 + nfeatures))
    load = multiplexer_general(tables, supports, outputs, seed)
    q = load.copy()
    phase_upper(q, model['gmask'], nfeatures, outputs)
    q.compose(load.inverse(), inplace=True)
    return transpile(q, basis_gates=['u3', 'cx'],
                     qubits_initially_zero=False, optimization_level=3)
