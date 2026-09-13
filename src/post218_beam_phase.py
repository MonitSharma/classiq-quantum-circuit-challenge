"""Beam-search depth-oriented synthesis of a CNOT+Rz phase polynomial.

The greedy scheduler in `post258_kernel_schedule` scores one layer at a time
from immediate hits only.  This module keeps a beam of partial schedules and
ranks them with an explicit potential: the total number of basis vectors still
needed to express every outstanding parity.  A CX(a, b) changes the coordinate
of every outstanding parity by `c_a ^= c_b`, so the potential change is
`n_b - 2 M[a][b]` with `M` the coordinate coincidence matrix.  That is exact
and cheap, which is what makes a beam affordable.

Correctness is structural: only CX and Rz are emitted, every requested parity
receives its angle exactly once, and the linear state is returned to identity.
"""
import random

import numpy as np
from qiskit import QuantumCircuit

from depth_parity_network import restore

POPCOUNT = np.array([bin(i).count('1') for i in range(1 << 12)], dtype=np.int64)


def _coords_matrix(inv, masks):
    """C[j, i] = coordinate i of parity masks[j] in the current wire basis."""
    if len(masks) == 0:
        return np.zeros((0, len(inv)), dtype=np.int64)
    t = np.asarray(masks, dtype=np.int64)
    return np.stack([POPCOUNT[inv[i] & t] & 1 for i in range(len(inv))], axis=1)


class _State:
    __slots__ = ('basis', 'inv', 'remaining', 'ops', 'times', 'score')

    def __init__(self, basis, inv, remaining, ops, times):
        self.basis = basis
        self.inv = inv
        self.remaining = remaining
        self.ops = ops
        self.times = times


def _flush(st, targets):
    for w, m in enumerate(st.basis):
        if m in st.remaining:
            st.ops = st.ops + (('rz', w, targets[m]),)
            st.remaining = st.remaining - {m}
            st.times = st.times[:w] + (st.times[w] + 1,) + st.times[w + 1:]


def _legal(mask, guard):
    """A wire may carry at most one guarded (ancilla) variable at a time."""
    return guard == 0 or (mask & guard).bit_count() <= 1


def _layers(st, rng, count, alpha, timew, noise, guard=0):
    """Candidate CX layers for one step, as lists of (control, target)."""
    n = len(st.basis)
    masks = sorted(st.remaining)
    c = _coords_matrix(st.inv, masks)
    counts = c.sum(axis=0)
    coincide = c.T @ c
    base = np.zeros((n, n))
    lowest = min(st.times)
    for a in range(n):
        for b in range(n):
            if a == b:
                continue
            new = st.basis[a] ^ st.basis[b]
            if not _legal(new, guard):
                base[a][b] = -1e9
                continue
            hit = 1.0 if new in st.remaining else 0.0
            delta = counts[b] - 2 * coincide[a][b]
            late = max(st.times[a], st.times[b]) - lowest
            base[a][b] = alpha * hit - delta - timew * late
    out = []
    for k in range(count):
        jitter = base + (rng.random() * noise if k else 0.0) * np.random.default_rng(
            rng.getrandbits(32)).standard_normal((n, n))
        order = sorted(((jitter[a][b], a, b) for a in range(n) for b in range(n) if a != b),
                       reverse=True)
        used, layer = set(), []
        for value, a, b in order:
            if a in used or b in used or value < -1e8:
                continue
            if layer and value <= 0:
                continue
            layer.append((a, b))
            used.update((a, b))
        if layer and layer not in out:
            out.append(layer)
    return out


def _apply(st, layer, targets):
    basis = list(st.basis)
    inv = list(st.inv)
    times = list(st.times)
    ops = st.ops
    for a, b in layer:
        basis[b] ^= basis[a]
        inv[a] ^= inv[b]
        moment = max(times[a], times[b]) + 1
        times[a] = times[b] = moment
        ops = ops + (('cx', a, b),)
    nxt = _State(tuple(basis), tuple(inv), st.remaining, ops, tuple(times))
    _flush(nxt, targets)
    return nxt


def _potential(st):
    if not st.remaining:
        return 0
    c = _coords_matrix(st.inv, sorted(st.remaining))
    return int(c.sum())


def _circuit(n, ops):
    q = QuantumCircuit(n)
    for op in ops:
        if op[0] == 'cx':
            q.cx(op[1], op[2])
        else:
            q.rz(-2 * op[2], op[1])
    return q


def psynth(n, targets, seed=0, beam=12, branch=6, alpha=4.0, timew=0.25, noise=1.0,
           global_phase=0.0, guard=0):
    """Synthesise exp(i * sum_m targets[m] * parity_m) as CX + Rz at low depth."""
    rng = random.Random(seed)
    start = _State(tuple(1 << w for w in range(n)), tuple(1 << w for w in range(n)),
                   frozenset(targets), (), (0,) * n)
    _flush(start, targets)
    states = [start]
    steps = 0
    while states[0].remaining:
        steps += 1
        assert steps < 4000, 'phase schedule did not converge'
        pool = []
        for st in states:
            if not st.remaining:
                pool.append(st)
                continue
            for layer in _layers(st, rng, branch, alpha, timew, noise, guard):
                pool.append(_apply(st, layer, targets))
        seen, uniq = set(), []
        for st in pool:
            key = (st.basis, st.remaining)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(st)
        uniq.sort(key=lambda s: (len(s.remaining), _potential(s), max(s.times)))
        states = uniq[:beam]
    best = None
    for st in states:
        if st.remaining:
            continue
        q = _circuit(n, st.ops)
        q.compose(restore(list(st.basis), n), inplace=True)
        q.global_phase = global_phase
        score = (q.depth(), q.size())
        if best is None or score < best[0]:
            best = (score, q)
    assert best is not None, 'no complete schedule in the final beam'
    return best[1]
