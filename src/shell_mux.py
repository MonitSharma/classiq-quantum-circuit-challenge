"""Five-input Shannon-split radius experiment.

This is deliberately a separate candidate generator.  It keeps the trusted
full_mux phase construction intact, but loads the three radius bits as
 h(y5,y0..y4) = h0(y0..y4) xor y5*delta(y0..y4).
The delta bank is cleared before the A/B/V bank is loaded, so the circuit
never assumes more than the six available clean ancillas.
"""

from pathlib import Path
import random

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile

from radius import R, truth
from mcz import phase_cube
from pair_search import pair_circuit


def multiplexer(tables, outputs, controls, axis, seed=0):
    """Emit the same Walsh/UCR construction as full_mux for arbitrary arity."""
    n = len(controls)
    N = 1 << n
    rng = random.Random(seed)
    base = list(range(n))
    rng.shuffle(base)
    shifts = list(range(n))
    rng.shuffle(shifts)
    orders = [base[s:] + base[:s] for s in shifts[:len(tables)]]

    coeffs = []
    for table, order in zip(tables, orders):
        a = np.array([
            np.pi * ((table >> sum(((k >> j) & 1) << v
                                    for j, v in enumerate(order))) & 1)
            for k in range(N)
        ])
        h = 1
        while h < N:
            for i in range(0, N, 2 * h):
                lo = a[i:i + h].copy()
                hi = a[i + h:i + 2 * h].copy()
                a[i:i + h] = lo + hi
                a[i + h:i + 2 * h] = lo - hi
            h *= 2
        coeffs.append(a / N)

    q = QuantumCircuit(18)
    for j in range(N):
        for b, target in enumerate(outputs):
            angle = float(coeffs[b][j ^ (j >> 1)])
            if abs(angle) > 1e-14:
                getattr(q, 'ry' if axis == 'y' else 'rz')(angle, target)
        pos = ((j + 1) & -(j + 1)).bit_length() - 1 if j < N - 1 else n - 1
        for b, target in enumerate(outputs):
            q.cx(controls[orders[b][pos]], target)
    return q


def split_tables(table):
    """Return h0 and h0 xor h1 as 5-bit lookup tables."""
    h0 = 0
    delta = 0
    for low in range(32):
        if (table >> low) & 1:
            h0 |= 1 << low
        if ((table >> low) & 1) ^ ((table >> (32 + low)) & 1):
            delta |= 1 << low
    return h0, delta


def split_radius_load(seed=0):
    """Load exact R0,R1,R2 using two five-input banks, then clear delta."""
    h0 = []
    delta = []
    for table in R:
        a, d = split_tables(table)
        h0.append(a)
        delta.append(d)

    q = multiplexer(h0, [12, 13, 14], list(range(6, 11)), 'y', seed)
    q.compose(multiplexer(delta, [15, 16, 17], list(range(6, 11)), 'y', seed + 1), inplace=True)
    for bit, target in enumerate([12, 13, 14]):
        q.ccx(11, 15 + bit, target)
    q.compose(multiplexer(delta, [15, 16, 17], list(range(6, 11)), 'y', seed + 2).inverse(), inplace=True)
    return q


def build(seed=0):
    a = truth(range(29, 54))
    b = truth(range(39, 44))
    v = truth(y for y in range(64) if any((table >> y) & 1 for table in R))
    radius_load = split_radius_load(seed)
    left_load = multiplexer([a, b, v], [15, 16, 17], list(range(6, 12)), 'y', seed + 10)

    q = radius_load.copy()
    q.compose(left_load, inplace=True)
    xs = truth(range(2, 27))
    xb = truth(range(27, 49))
    xo = ((1 << 64) - 1) ^ xs ^ xb
    q.cx(17, 15)
    q.cx(17, 16)
    q.compose(multiplexer([xs, xb, xo], [15, 16, 17], list(range(6)), 'z', seed + 10000), inplace=True)
    q.z(17)
    q.cx(17, 16)
    q.cx(17, 15)

    fold = QuantumCircuit(18)
    for k in range(4):
        fold.cx(11, k)
    fold.x(3)
    for k in range(3):
        fold.cx(3, k)
    fold.x(3)
    q.compose(fold, inplace=True)

    comp = QuantumCircuit(18)
    comp.x([0, 1, 2])
    carry = 3
    for i in range(3):
        comp.cx(12 + i, i)
        comp.cx(12 + i, carry)
        comp.rccx(carry, i, 12 + i)
        carry = 12 + i
    q.compose(comp, inplace=True)
    q.cx(11, 4)
    q.x(4)
    phase_cube(q, frozenset([18, 6, 5, 15]), [])
    q.x(4)
    q.cx(11, 4)
    q.compose(comp.inverse(), inplace=True)
    q.compose(fold.inverse(), inplace=True)
    q.compose(left_load.inverse(), inplace=True)
    q.compose(radius_load.inverse(), inplace=True)
    q.compose(pair_circuit(truth([32, 48]), truth(range(17, 22))), inplace=True)
    return transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False, optimization_level=3)


if __name__ == '__main__':
    best = None
    for seed in range(8):
        candidate = build(seed)
        print(seed, candidate.depth(), candidate.count_ops(), flush=True)
        if best is None or candidate.depth() < best.depth():
            best = candidate
            Path(f'artifacts/shell_mux_seed{seed}.qasm').write_text(qasm2.dumps(candidate))
