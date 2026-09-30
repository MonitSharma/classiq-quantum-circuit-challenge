"""Isolate the constant-adder depth: chain carries vs the recorded ladder.

Everything else in the arithmetic route is already measured.  The open number is
how deep "add a constant to a five-bit register" really is, because the recorded
ladder builds each carry as a widening multi-controlled X.
"""
import json, sys
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2

sys.path.insert(0, 'src')
from distributed_frame_search import native
from post190_y_fold import add_const as ladder_add_const


def add_const_chain(q, reg, value, carry_wires, control=None):
    n = len(reg)
    bits = [(value >> i) & 1 for i in range(n)]
    c = [None] * n
    for i in range(n - 1):
        prev, tgt, a = c[i], carry_wires[i], reg[i]
        if bits[i]:
            if prev is None:
                q.cx(a, tgt)
            else:
                q.cx(prev, tgt); q.cx(a, tgt); q.ccx(a, prev, tgt)
            c[i + 1] = tgt
        elif prev is not None:
            q.ccx(a, prev, tgt)
            c[i + 1] = tgt
    for i in range(n):
        if bits[i]:
            q.x(reg[i])
        if c[i] is not None:
            q.cx(c[i], reg[i])
    if control is not None:
        for w in carry_wires[:n - 1]:
            q.cx(control, w)


def sim(circuit, value):
    bits = [(value >> i) & 1 for i in range(circuit.num_qubits)]
    for inst in circuit.data:
        w = [circuit.find_bit(b).index for b in inst.qubits]
        n = inst.operation.name
        if n == 'x':
            bits[w[0]] ^= 1
        elif n == 'cx':
            bits[w[1]] ^= bits[w[0]]
        elif n in ('rccx', 'ccx'):
            bits[w[2]] ^= bits[w[0]] & bits[w[1]]
        else:
            raise AssertionError(n)
    return sum(b << i for i, b in enumerate(bits))


def value_of(word):
    return word & 31


def test(value, ctrl=False):
    n = 10
    q = QuantumCircuit(n)
    add_const_chain(q, [0, 1, 2, 3, 4], value, [5, 6, 7, 8], control=(9 if ctrl else None))
    bad = 0
    for a in range(32):
        for cbit in ((0, 1) if ctrl else (0,)):
            inp = a | (cbit << 9)
            got = value_of(sim(q, inp))
            want = (a + (value if (cbit or not ctrl) else 0)) % 32
            if got != want:
                bad += 1
    return q, bad


if __name__ == '__main__':
    rows = []
    for value, ctrl in ((13, False), (10, True), (13, True)):
        q, bad = test(value, ctrl)
        nq = native(q)
        rows.append(dict(value=value, controlled=ctrl, mismatches=bad,
                         depth=nq.depth(), cx=nq.count_ops().get('cx', 0)))
        print(rows[-1], flush=True)
    # ladder baseline for the same operation
    q = QuantumCircuit(10)
    ladder_add_const(q, 13, helpers=[5, 6, 7], control=None)
    nq = native(q)
    print(dict(value=13, controlled=False, ladder=True, depth=nq.depth(),
               cx=nq.count_ops().get('cx', 0)), flush=True)
    Path('artifacts/adder_depth').mkdir(parents=True, exist_ok=True)
    Path('artifacts/adder_depth/report.json').write_text(json.dumps(rows, indent=2))
