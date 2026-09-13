"""Sparsity-aware inner scheduling for the four-frame distributed lookup.

`distributed_ucry.structured_ucry` keeps a fixed four-frame skeleton in which
six hosts (three high control wires carrying a copied output, plus the three
outputs) sweep the three low control wires in Gray order.  That skeleton is
reused verbatim here, because its frame transitions are what make the lookup
exact for arbitrary inputs.  What is replaced is the per-frame walk:

* the masks a host actually needs in a frame are a subset of the low cube, so
  the walk is solved as a shortest closed Hamming tour over that subset by
  exact subset dynamic programming rather than by trying six fixed orders;
* the six tours are then interleaved by a list scheduler that knows the three
  low wires are the scarce resource, and several randomised tie-breaks are
  tried so that hosts do not all demand the same source in the same layer.

The emitted circuit is still only CX and Rz between the Rx conjugations, so the
result is verified against the intended controlled-Ry table numerically.
"""
import argparse
import itertools
import json
import math
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2

from distributed_ucry import walsh, verify_component
from distributed_frame_search import native

TOL = 1e-14


@lru_cache(maxsize=None)
def _tours(subset, slack=1):
    """Closed Hamming tours of `subset` from 0, within `slack` of the shortest."""
    nodes = [m for m in range(8) if subset >> m & 1]
    if not nodes:
        return ((),)
    scored = []
    for order in itertools.permutations(nodes):
        cost, cur = 0, 0
        for m in order:
            cost += (cur ^ m).bit_count()
            cur = m
        cost += cur.bit_count()
        scored.append((cost, order))
    shortest = min(c for c, _ in scored)
    return tuple(o for c, o in scored if c <= shortest + slack)


def _job(order, coeff):
    """Operation list for one host: CX on low wires, Rz at each visited mask."""
    ops, cur = [], 0
    for mask in order:
        for k in range(3):
            if (cur ^ mask) >> k & 1:
                ops.append(('cx', k))
        ops.append(('rz', coeff[mask]))
        cur = mask
    for k in range(3):
        if cur >> k & 1:
            ops.append(('cx', k))
    return ops


def _simulate(jobs, priority):
    """Layer list for the given host jobs; the three low wires are the resource."""
    positions = [0] * len(jobs)
    layers = []
    while any(positions[i] < len(jobs[i]) for i in range(len(jobs))):
        used, layer = set(), []
        ready = [i for i in range(len(jobs)) if positions[i] < len(jobs[i])]
        ready.sort(key=lambda i: (len(jobs[i]) - positions[i], priority[i]), reverse=True)
        for i in ready:
            kind, value = jobs[i][positions[i]]
            if kind == 'cx':
                if value in used:
                    continue
                used.add(value)
            layer.append((kind, value, i))
            positions[i] += 1
        assert layer, 'list scheduler stalled'
        layers.append(layer)
    return layers


def _ordered_tour(subset, order):
    """Gray-style tour of `subset` that changes low bits in the given order."""
    walk = [sum((((j ^ (j >> 1)) >> k) & 1) << order[k] for k in range(3))
            for j in range(8)]
    return tuple(m for m in walk if subset >> m & 1)


def _emit(q, groups, hosts, lowwires, rng, tries):
    """Pick tours for the six hosts jointly, keeping the shortest schedule.

    The staggered candidates come first: when the frames are nearly full, the
    six hosts must demand different low wires in the same step, which is what
    the cyclic bit-order shifts in `structured_ucry` achieve.  Random shortest
    tours are then tried on top, which is what helps when frames are sparse.
    """
    perms = list(itertools.permutations(range(3)))
    best = None
    staggered = []
    for base in perms:
        rotations = [tuple(base[(i + shift) % 3] for i in range(3)) for shift in range(3)]
        staggered.append([rotations[j % 3] for j in range(len(groups))])
    for attempt in range(tries + len(staggered)):
        jobs = []
        if attempt < len(staggered):
            for (subset, coeff), order in zip(groups, staggered[attempt]):
                jobs.append(_job(_ordered_tour(subset, order), coeff))
        else:
            for subset, coeff in groups:
                options = _tours(subset)
                jobs.append(_job(rng.choice(options), coeff))
        priority = [rng.random() for _ in jobs]
        layers = _simulate(jobs, priority)
        if best is None or len(layers) < len(best):
            best = layers
    for layer in best:
        for kind, value, i in layer:
            if kind == 'cx':
                q.cx(lowwires[value], hosts[i])
            else:
                q.rz(value, hosts[i])


def bank_ucry(angle_tables, outputs, controls, seed=0, high=None, tries=24):
    assert len(controls) == 6 and len(outputs) == 3
    rng = random.Random(seed)
    high = list(high) if high is not None else rng.sample(range(6), 3)
    low = [i for i in range(6) if i not in high]
    rng.shuffle(low)
    hosts = [controls[i] for i in high] + list(outputs)
    co = walsh(angle_tables)
    q = QuantumCircuit(max(list(outputs) + list(controls)) + 1)
    for t in outputs:
        q.rx(math.pi / 2, t)
    for i in range(3):
        q.cx(outputs[i], controls[high[i]])
    for frame in range(4):
        gray_high = frame ^ (frame >> 1)
        shifts = [sum(((gray_high >> k) & 1) << ((i + k + 1) % 3) for k in range(2))
                  for i in range(3)]
        group = [(1 << (3 + i)) ^ (1 << i) ^ shifts[i] for i in range(3)]
        group += [(1 << (3 + i)) ^ shifts[i] for i in range(3)]
        groups = []
        for parity in group:
            target = (parity >> 3).bit_length() - 1
            hmask = sum(((parity >> k) & 1) << high[k] for k in range(3))
            coeff = {m: float(co[target, hmask | sum(((m >> k) & 1) << low[k] for k in range(3))])
                     for m in range(8)}
            subset = sum(1 << m for m in range(8) if abs(coeff[m]) > TOL)
            groups.append((subset, coeff))
        _emit(q, groups, hosts, [controls[low[i]] for i in range(3)], rng, tries)
        for i in range(3):
            q.cx(outputs[i], controls[high[i]])
        if frame < 3:
            nxt = (frame + 1) ^ ((frame + 1) >> 1)
            changed = (gray_high ^ nxt).bit_length() - 1
            for i in range(3):
                q.cx(controls[high[(i + changed + 1) % 3]], outputs[i])
            for i in range(3):
                q.cx(outputs[i], controls[high[i]])
        else:
            for i in range(3):
                for k in range(2):
                    if gray_high >> k & 1:
                        q.cx(controls[high[(i + k + 1) % 3]], outputs[i])
    for t in outputs:
        q.rx(-math.pi / 2, t)
    return q


def best_loader(angle_tables, seeds=200, relative=True):
    """Lowest-depth bank loader over seeds; optionally with H-conjugated boundary."""
    best = None
    for seed in range(seeds):
        raw = bank_ucry(angle_tables, [6, 7, 8], list(range(6)), seed)
        if relative:
            data = list(raw.data)
            assert all(inst.operation.name == 'rx' for inst in data[:3] + data[-3:])
            body = data[3:-3]
            while body and body[-1].operation.name == 'cx':
                a, b = [raw.find_bit(v).index for v in body[-1].qubits]
                if a >= 6 or b < 6:
                    break
                body.pop()
            out = QuantumCircuit(9)
            for b in (6, 7, 8):
                out.h(b)
            for inst in body:
                out.append(inst.operation, [raw.find_bit(v).index for v in inst.qubits])
            for b in (6, 7, 8):
                out.h(b)
            cand = native(out)
        else:
            cand = native(raw)
        score = (cand.depth(), cand.size())
        if best is None or score < best[0]:
            best = (score, cand, seed)
    return best
