"""End-to-end build: class codes -> low-degree kernel -> loaders -> oracle.

Everything is derived from the explicit per-coordinate code assignment, so the
kernel truth table, the reachable set and the loader angle tables can never
disagree about which raw parity is used as the fourth code bit.
"""
import hashlib
import math

import numpy as np
from qiskit import QuantumCircuit, qasm2

from distributed_frame_search import native
from depth_parity_network import walsh as walsh1
from post218_beam_phase import psynth
from post218_bank_loader import best_loader
from two_stage_oracle import logo

ORDER = sorted(range(256), key=lambda m: (m.bit_count(), m))
EVAL = [sum(1 << i for i, m in enumerate(ORDER) if m & ~w == 0) for w in range(256)]
KERNEL_WIRES = [11, 12, 13, 14, 4, 15, 16, 17]


def kernel_spec(ycode, xcode):
    """Reachable (code pair -> value) map; unreachable pairs stay free."""
    want = {}
    for y in range(64):
        for x in range(64):
            key = ycode[y] | (xcode[x] << 4)
            value = 1 if logo(x, y) else 0
            if key in want:
                assert want[key] == value, 'code does not determine the predicate'
            want[key] = value
    return want


def low_degree_anf(want):
    """Lowest-degree GF(2) polynomial agreeing with `want` on reachable points."""
    piv = {}
    for w, value in want.items():
        row, rhs = EVAL[w], value
        while row:
            i = (row & -row).bit_length() - 1
            if i in piv:
                a, b = piv[i]
                row ^= a
                rhs ^= b
            else:
                piv[i] = (row, rhs)
                break
        assert row or rhs == 0, 'inconsistent kernel constraints'
    sol = 0
    for i in sorted(piv, reverse=True):
        row, rhs = piv[i]
        if ((row & sol).bit_count() & 1) ^ rhs:
            sol |= 1 << i
    terms = [ORDER[i] for i in range(256) if sol >> i & 1]
    for w, value in want.items():
        assert sum(int(m & ~w == 0) for m in terms) % 2 == value
    return terms


def kernel_phases(terms):
    return math.pi * np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], float)


def build_kernel(phases, seeds=40, cfgs=((40, 10, 5.0, 0.35), (24, 8, 3.0, 0.3))):
    co = walsh1(phases)
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    best = None
    for seed in range(seeds):
        for beam, branch, alpha, timew in cfgs:
            q = native(psynth(8, targets, seed=seed, beam=beam, branch=branch, alpha=alpha,
                              timew=timew, global_phase=float(co[0])))
            score = (q.depth(), q.count_ops().get('cx', 0))
            if best is None or score < best[0]:
                best = (score, q, (seed, beam, branch, alpha, timew))
    return best, len(targets)


def verify_kernel(circuit, phases):
    from qiskit.quantum_info import Operator
    op = Operator(qasm2.loads(qasm2.dumps(circuit))).data
    want = np.diag(np.exp(1j * phases))
    overlap = np.vdot(want, op)
    return float(np.max(abs(op - overlap / abs(overlap) * want)))


def angle_table(code):
    return np.array([[math.pi * ((code[v] >> b) & 1) for v in range(64)] for b in range(1, 4)])


def assemble(ycode, xcode, kern, yload, xload, ycx=None, xcx=None):
    enc = QuantumCircuit(18)
    ey = yload.copy()
    if ycx:
        ey.cx(*ycx)
    ex = xload.copy()
    if xcx:
        ex.cx(*xcx)
    enc.compose(ey, list(range(6, 12)) + [12, 13, 14], inplace=True)
    enc.compose(ex, list(range(6)) + [15, 16, 17], inplace=True)
    return native(enc.compose(kern, KERNEL_WIRES).compose(enc.inverse()))


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()
