"""Narrow-address structured UCRy loader.

Generalises distributed_ucry.structured_ucry to m address controls
(3 <= m <= 6).  The four-basis, three-layer-transition structure is
unchanged; only the number of Gray steps per stage changes, from 2^(m-3).
Hosts are the three "high" address wires plus the three outputs, so the
host count (and therefore the transition cost) is independent of m.
"""
from __future__ import annotations
import math, random
import numpy as np
from qiskit import QuantumCircuit


def walsh(tables):
    a = np.asarray(tables, float).copy()
    h = 1
    while h < a.shape[1]:
        for i in range(0, a.shape[1], 2*h):
            lo = a[:, i:i+h].copy(); hi = a[:, i+h:i+2*h].copy()
            a[:, i:i+h] = lo+hi; a[:, i+h:i+2*h] = lo-hi
        h *= 2
    return a/a.shape[1]


def structured_ucry_m(angle_tables, outputs, controls, seed=0, high=None):
    """Exact multi-output Ry lookup on an m-variable address."""
    m = len(controls)
    assert 3 <= m <= 6 and len(outputs) == 3
    assert len(set(list(controls)+list(outputs))) == m+3
    L = m - 3
    rng = random.Random(seed)
    high = list(high) if high is not None else rng.sample(range(m), 3)
    low = [i for i in range(m) if i not in high]
    rng.shuffle(low)
    assert len(low) == L
    hosts = [controls[i] for i in high] + list(outputs)
    co = walsh(angle_tables)
    assert co.shape[1] == (1 << m)
    q = QuantumCircuit(max(list(outputs)+list(controls))+1)
    for t in outputs:
        q.rx(math.pi/2, t)
    for i in range(3):
        q.cx(outputs[i], controls[high[i]])
    orders = [low[(i % L):] + low[:(i % L)] for i in range(6)]
    steps = 1 << L
    prev_gray = 0
    for stage in range(4):
        gray_high = stage ^ (stage >> 1)
        shifts = [sum(((gray_high >> k) & 1) << ((i+k+1) % 3) for k in range(2))
                  for i in range(3)]
        group = [(1 << (3+i)) ^ (1 << i) ^ shifts[i] for i in range(3)]
        group += [(1 << (3+i)) ^ shifts[i] for i in range(3)]
        for step in range(steps):
            gray = step ^ (step >> 1)
            for j, parity in enumerate(group):
                target = (parity >> 3).bit_length()-1
                hmask = sum(((parity >> k) & 1) << high[k] for k in range(3))
                lmask = sum(((gray >> k) & 1) << orders[j][k] for k in range(L))
                theta = float(co[target, hmask | lmask])
                if abs(theta) > 1e-14:
                    q.rz(theta, hosts[j])
            nxt = ((step+1) ^ ((step+1) >> 1)) if step < steps-1 else 0
            diff = gray ^ nxt
            bit = diff.bit_length()-1
            for j in range(6):
                q.cx(controls[orders[j][bit]], hosts[j])
        prev_gray = gray_high
        for i in range(3):
            q.cx(outputs[i], controls[high[i]])
        if stage < 3:
            next_gray = (stage+1) ^ ((stage+1) >> 1)
            changed = (gray_high ^ next_gray).bit_length()-1
            for i in range(3):
                q.cx(controls[high[(i+changed+1) % 3]], outputs[i])
            for i in range(3):
                q.cx(outputs[i], controls[high[i]])
        else:
            for i in range(3):
                for k in range(2):
                    if gray_high >> k & 1:
                        q.cx(controls[high[(i+k+1) % 3]], outputs[i])
    for t in outputs:
        q.rx(-math.pi/2, t)
    return q


def verify_component(circuit, tables, m):
    """Exact unitary check of the 9-wire block against the angle tables."""
    from qiskit import qasm2
    from qiskit.quantum_info import Operator
    op = Operator(qasm2.loads(qasm2.dumps(circuit))).data
    expected = np.zeros_like(op)
    for address in range(1 << m):
        block = np.array([[1.0]])
        for bit in reversed(range(3)):
            theta = tables[bit][address]
            c, s = math.cos(theta/2), math.sin(theta/2)
            block = np.kron(block, [[c, -s], [s, c]])
        idx = [address+((1 << m)*t) for t in range(8)]
        expected[np.ix_(idx, idx)] = block
    overlap = np.vdot(expected, op)
    phase = overlap/abs(overlap)
    return float(np.max(np.abs(op - phase*expected)))
