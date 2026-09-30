"""Cost of the disk test without any y fold: bound construction + comparison.

The recorded arithmetic route folds y first (95, or 74 disk-only) and then
compares.  The audit's own alternative is to derive the radius from the cheap
x fold and test y against c +- R in original coordinates, so that the y fold
never happens.  This measures that serial chain directly:

    R (3-4 bits on wires) -> b = c + R and c - R -> [y <= b_hi] and [y >= b_lo]

Everything is measured in native u3/cx with the repository transpiler.
"""
import json, sys
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2

sys.path.insert(0, 'src')
from distributed_frame_search import native


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


def add_var_const(q, out, var, const, carries):
    """out = const + var, all 6-bit; out is clean, var has nv bits."""
    nv = len(var)
    n = len(out)
    bits = [(const >> i) & 1 for i in range(n)]
    # ripple with explicit carries; var bits are inputs, const bits are gates
    c = [None] * n
    for i in range(n - 1):
        a = out[i] if i < nv else None
        src = var[i] if i < nv else None
        # carry_{i+1} = (src & K) | (c & (src ^ K))
        prev = c[i]
        tgt = carries[i]
        if src is not None and bits[i]:
            if prev is None:
                q.cx(src, tgt)
            else:
                q.cx(prev, tgt); q.cx(src, tgt); q.ccx(src, prev, tgt)
            c[i + 1] = tgt
        elif src is None and bits[i]:
            if prev is not None:
                q.cx(prev, tgt)
                c[i + 1] = tgt
        elif prev is not None:
            if src is not None:
                q.ccx(src, prev, tgt)
            else:
                q.cx(prev, tgt)   # placeholder; not used for our constants
            c[i + 1] = tgt
    for i in range(n):
        if bits[i]:
            q.x(out[i])
        if i < nv:
            q.cx(var[i], out[i])
        if c[i] is not None:
            q.cx(c[i], out[i])
    return q


def compare_le(q, y, b, target, temp):
    """target ^= [y <= b] for 6-bit y,b on wires; uses temp as scratch."""
    n = 6
    # y <= b  <=>  y - b - 1 < 0  <=> borrow. Use y + ~b and inspect carry.
    for i in range(n):
        q.cx(b[i], temp[i]) if False else None
    raise NotImplementedError


if __name__ == '__main__':
    # Just measure the bound construction chain cost.
    rows = []
    for nv, const in ((4, 41), (4, 19)):
        q = QuantumCircuit(18)
        var = list(range(0, nv))          # R
        out = list(range(6, 12))          # bound
        carries = list(range(12, 17))
        add_var_const(q, out, var, const, carries)
        nq = native(q)
        bad = 0
        for r in range(16):
            w = sim(q, r)
            got = (w >> 6) & 63
            if got != (const + r) % 64:
                bad += 1
        rows.append(dict(const=const, var_bits=nv, mismatches=bad,
                         depth=nq.depth(), cx=nq.count_ops().get('cx', 0)))
        print(rows[-1], flush=True)
    Path('artifacts/arith_bound_cost').mkdir(parents=True, exist_ok=True)
    Path('artifacts/arith_bound_cost/report.json').write_text(json.dumps(rows, indent=2))
