"""Carry-lookahead re-implementation of the constant adder used by the y fold.

The recorded y fold (post190_y_fold) measures 95 layers, or 74 for the disk-only
y5-band variant, because add_const builds the carry with a ladder of
multi-controlled X gates: each carry is a fresh multi-control gate whose
controls include every lower bit.  A direct carry recurrence

    c_{i+1} = (a_i & K_i) | (c_i & (a_i ^ K_i))

needs only one Toffoli per carry position regardless of i, so the depth is set
by the number of carry positions, not by a widening control set.  This module
measures that difference on the identical fold contract.
"""
import json, math, sys, itertools
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2

sys.path.insert(0, 'src')
from distributed_frame_search import native
from two_stage_oracle import ROWCLS


def add_const_front(q, value, reg, carries, control=None):
    """reg += value mod 2^len(reg); carries are clean helper wires (len(reg)-1)."""
    n = len(reg)
    bits = [(value >> i) & 1 for i in range(n)]
    # carry chain: c[i] is the carry INTO position i, i=0 has no carry
    prev = None
    for i in range(n - 1):
        tgt = carries[i]
        a = reg[i]
        if bits[i]:
            # carry_{i+1} = a | c  = a ^ c ^ (a & c)
            if prev is None:
                q.cx(a, tgt)
            else:
                q.cx(prev, tgt)
                q.cx(a, tgt)
                q.ccx(a, prev, tgt)
        else:
            if prev is None:
                pass                      # carry_{i+1} = 0
            else:
                q.ccx(a, prev, tgt)
        prev = tgt if (bits[i] or prev is not None) else None
    # sums
    for i in range(n):
        if bits[i]:
            q.x(reg[i])
        if i > 0:
            c = carries[i - 1]
            if c is not None:
                q.cx(c, reg[i])
    if control is not None:
        for c in carries[:n - 1]:
            q.cx(control, c)


def build_fold(fast=True):
    """y -> (band, sign, magnitude): centres 19 (band 0) and 9 (band 1)."""
    q = QuantumCircuit(11)
    reg = [0, 1, 2, 3, 4]
    carries = [6, 7, 8, 9]
    band = 5
    # band = [y >= 28] = y5 xor (y4 y3 y2 and not y5)
    h = [10]
    q.ccx(4, 3, h[0])
    # y4 y3 y2 = y4 & (y3&y2)
    q.ccx(3, 2, 10) if False else None
    q = QuantumCircuit(11)
    # cleaner: h0 = y4&y3 ; h0 = h0&y2 ; band = y5 xor (h0 & ~y5)
    q.ccx(4, 3, 10)
    q.ccx(10, 2, 10)
    q.cx(10, 5)
    q.x(5)
    q.ccx(10, 5, 5)
    q.x(5)
    q.ccx(10, 2, 10)
    q.ccx(4, 3, 10)
    add_const_front(q, (-19) % 32, reg, carries)
    # conditional +10 when band is set: apply the same adder controlled on band
    ctrl = QuantumCircuit(11)
    add_const_front(ctrl, 10, reg, carries, control=5)
    q.compose(ctrl, inplace=True)
    for i in range(4):
        q.cx(4, i)
    return q


def simulate(circuit, value):
    bits = [(value >> i) & 1 for i in range(circuit.num_qubits)]
    for inst in circuit.data:
        w = [circuit.find_bit(b).index for b in inst.qubits]
        name = inst.operation.name
        if name == 'x':
            bits[w[0]] ^= 1
        elif name == 'cx':
            bits[w[1]] ^= bits[w[0]]
        elif name in ('rccx', 'ccx'):
            bits[w[2]] ^= bits[w[0]] & bits[w[1]]
        else:
            raise AssertionError(name)
    return sum(b << i for i, b in enumerate(bits))


def check(circuit):
    bad = 0
    for y in range(64):
        out = simulate(circuit, y)
        band = (out >> 5) & 1
        if band != int(y >= 28):
            bad += 1
            continue
        d = ((y & 31) - (19 if band == 0 else 9)) % 32
        sign = (out >> 4) & 1
        mag = out & 15
        if sign != (d >> 4) or mag != ((d & 15) ^ (15 if sign else 0)):
            bad += 1
    return bad


if __name__ == '__main__':
    for fast in (True,):
        raw = build_fold(fast)
        bad = check(raw)
        q = native(raw)
        print(dict(fast=fast, mismatches=bad, depth=q.depth(),
                   cx=q.count_ops().get('cx', 0), width=q.num_qubits), flush=True)
        Path('artifacts/post190_y_fold_fast').mkdir(parents=True, exist_ok=True)
        Path('artifacts/post190_y_fold_fast/y_fold_fast.qasm').write_text(qasm2.dumps(q))
        Path('artifacts/post190_y_fold_fast/report.json').write_text(json.dumps(
            dict(fast=fast, mismatches=bad, depth=q.depth(), cx=q.count_ops().get('cx', 0),
                 width=q.num_qubits, baseline_ladder=95, baseline_disk_only=74), indent=2))
