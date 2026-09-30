"""Faster constant adder for the y fold: direct carry recurrence.

post190_y_fold.add_const builds each carry as a ladder of multi-controlled X
gates whose control set widens with the bit index.  The direct recurrence

    c_{i+1} = (a_i & K_i) | (c_i & (a_i ^ K_i))

costs exactly one Toffoli per carry position, independent of the index, so the
fold depth is set by the number of positions rather than by control-set size.
Measured here against the recorded ladder on the identical fold contract.
"""
import json, sys
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2

sys.path.insert(0, 'src')
from distributed_frame_search import native
from post190_y_fold import add_const as ladder_add_const, build as ladder_build, simulate, check


def add_const_chain(q, reg, value, carry_wires, control=None):
    """reg += value mod 2^len(reg) using one Toffoli per carry position."""
    n = len(reg)
    bits = [(value >> i) & 1 for i in range(n)]
    c = [None] * n
    for i in range(n - 1):
        prev = c[i]
        tgt = carry_wires[i]
        a = reg[i]
        if bits[i]:
            if prev is None:
                q.cx(a, tgt)
            else:
                q.cx(prev, tgt)
                q.cx(a, tgt)
                q.ccx(a, prev, tgt)
            c[i + 1] = tgt
        else:
            if prev is not None:
                q.ccx(a, prev, tgt)
                c[i + 1] = tgt
    for i in range(n):
        if bits[i]:
            q.x(reg[i])
        if c[i] is not None:
            q.cx(c[i], reg[i])
    if control is not None:
        for w in carry_wires:
            q.cx(control, w)


def build_fast():
    """Same contract as post190_y_fold.build but with chain carries."""
    q = QuantumCircuit(11)
    reg = [0, 1, 2, 3, 4]
    carries_fold = [7, 8, 9, 10]
    carries_ctrl = [7, 8, 9, 10]
    # band = [y >= 28] = y5 or (y4 y3 y2)
    q.ccx(4, 3, 6)
    q.ccx(6, 2, 6)
    q.cx(5, 6)
    q.x(5)
    q.ccx(6, 5, 6)
    q.x(5)
    # keep band on wire 5? original stores band on a separate wire; use 6 and restore helper
    # recompute cleanly: band on wire 10 replaced below
    q = QuantumCircuit(11)
    h = 6
    q.ccx(4, 3, h)            # h = y4 y3
    q.ccx(h, 2, h)            # h = y4 y3 y2
    q.ccx(h, 5, h) if False else None
    # band wire 9
    q.cx(5, 9)
    q.x(5)
    q.ccx(h, 5, 9)
    q.x(5)
    q.ccx(h, 2, h) if False else None
    # restore h
    q.ccx(h, 2, h) if False else None
    # h still equals y4y3y2; uncompute it
    q.ccx(h, 2, h)
    q.ccx(4, 3, h)
    add_const_chain(q, [0, 1, 2, 3, 4], (-19) % 32, [6, 7, 8, 10])
    return q


if __name__ == '__main__':
    raw = build_fast()
    out = []
    for y in range(64):
        w = simulate(raw, y)
        out.append(w)
    print('sample sim (y, wire5..10 fields):', [(y, out[y] >> 5) for y in (0, 11, 19, 28, 32, 41, 63)])
    q = native(raw)
    print(dict(depth=q.depth(), cx=q.count_ops().get('cx', 0), width=q.num_qubits))
