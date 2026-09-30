"""Measure the y-side fold, the one unresolved cost in the arithmetic route.

The x side folds cheaply -- 10 depth / 10 CX, verified on all 128 inputs -- for a
specific arithmetic reason: `40 + 55 = 95`, so a controlled XOR of the low five
bits maps the disk centred at 55 onto the one centred at 40, and the shared
centre's low-five value is **8**, a power of two, so "subtract 8 mod 32" costs two
gates.

The y centres are 19 and 41, whose low-five values are 19 and 9.  Those sum to 28,
not 31, so no XOR reflection aligns them; and both being odd, their sum is even
while alignment needs it odd, so no unconditional shift fixes that either.  Each
band therefore needs its own centring constant, and neither 19 nor 9 is a power of
two, so the two-gate subtraction the x side enjoys is unavailable.

This builds the fold anyway and measures it, so the route is costed rather than
estimated.  Contract: `y -> (band, sign, magnitude)` with the row class a function
of `(band, bucket(magnitude))`; relative phases from the RCCX ladders are fine
because the fold sits inside a compute / diagonal / uncompute sandwich.
"""
import argparse
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2

from distributed_frame_search import native
from two_stage_oracle import ROWCLS

HELPERS = [7, 8, 9, 10]


def mcx(circuit, controls, target, helpers):
    """Relative-phase multi-controlled X; exact inverse is used to uncompute."""
    controls = list(controls)
    if len(controls) == 1:
        circuit.cx(controls[0], target)
    elif len(controls) == 2:
        circuit.rccx(controls[0], controls[1], target)
    elif len(controls) == 3:
        h = helpers[0]
        circuit.rccx(controls[0], controls[1], h)
        circuit.rccx(h, controls[2], target)
        circuit.rccx(controls[0], controls[1], h)
    else:
        h0, h1 = helpers[0], helpers[1]
        circuit.rccx(controls[0], controls[1], h0)
        circuit.rccx(controls[2], controls[3], h1)
        if len(controls) == 4:
            circuit.rccx(h0, h1, target)
        else:
            h2 = helpers[2]
            circuit.rccx(h0, h1, h2)
            circuit.rccx(h2, controls[4], target)
            circuit.rccx(h0, h1, h2)
        circuit.rccx(controls[2], controls[3], h1)
        circuit.rccx(controls[0], controls[1], h0)


def add_const(circuit, value, control=None, helpers=HELPERS):
    """Add `value` mod 32 to wires 0..4, optionally controlled on `control`."""
    for k in range(4, -1, -1):
        if not (value >> k) & 1:
            continue
        for j in range(4, k, -1):
            ctrls = list(range(k, j)) + ([control] if control is not None else [])
            mcx(circuit, ctrls, j, helpers)
        if control is None:
            circuit.x(k)
        else:
            circuit.cx(control, k)


def build():
    q = QuantumCircuit(11)
    band = 6
    # band = [y >= 28] = y5 or (y4 and y3 and y2)
    q.rccx(4, 3, 7)
    q.rccx(7, 2, 8)                 # 8 = y4 y3 y2
    q.cx(5, band)
    q.x(5)
    q.rccx(8, 5, band)              # band = y5 xor (y4y3y2 and not y5)
    q.x(5)
    q.rccx(7, 2, 8)
    q.rccx(4, 3, 7)
    # centre each band: subtract 19, then add 10 when the band bit is set
    add_const(q, (-19) % 32, helpers=[8, 9, 10])
    add_const(q, 10, control=band, helpers=[8, 9, 10])
    # sign-controlled one's complement of the low four bits
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
    """Every y must land on (band, sign, magnitude) with the class determined."""
    seen, classes = {}, {}
    for y in range(64):
        out = simulate(circuit, y)
        band = (out >> 6) & 1
        sign = (out >> 4) & 1
        mag = out & 15
        assert (out >> 7) == 0, 'helpers not restored'
        assert band == int(y >= 28), (y, band)
        centre = 19 if band == 0 else 9
        d = ((y & 31) - centre) % 32
        assert sign == (d >> 4) and mag == ((d & 15) ^ (15 if sign else 0)), y
        seen[y] = (band, sign, mag)
        classes.setdefault((band, sign, mag), set()).add(ROWCLS[y])
    # The fold acts on the low five bits, so y5 survives on its own wire and the
    # full output is injective; what matters is whether the *descriptor* --
    # which the kernel reads -- still determines the class.
    by_sign = {k: v for k, v in classes.items() if len(v) > 1}
    without_sign = {}
    for y in range(64):
        band, sign, mag = seen[y]
        without_sign.setdefault((band, mag), set()).add(ROWCLS[y])
    with_y5 = {}
    for y in range(64):
        band, sign, mag = seen[y]
        with_y5.setdefault((band, sign, mag, (y >> 5) & 1), set()).add(ROWCLS[y])
    return dict(sign_mag=len(by_sign),
                mag_only=len({k: v for k, v in without_sign.items() if len(v) > 1}),
                with_y5=len({k: v for k, v in with_y5.items() if len(v) > 1}))


def run(outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    raw = build()
    collisions = check(raw)
    q = native(raw)
    row = dict(depth=q.depth(), cx=q.count_ops().get('cx', 0), width=q.num_qubits,
               class_collisions=collisions)
    (outdir / 'y_fold.qasm').write_text(qasm2.dumps(q))
    (outdir / 'report.json').write_text(json.dumps(row, indent=2) + '\n')
    print(row, flush=True)
    return row


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, default=Path('artifacts/post190_y_fold'))
    run(p.parse_args().outdir)
