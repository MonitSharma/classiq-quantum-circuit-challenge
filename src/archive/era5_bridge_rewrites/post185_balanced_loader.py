"""Balanced stage assignment for the structured three-bit code loader.

`distributed_ucry.structured_ucry` hosts the twenty-four (output, high-mask)
parity groups on four bases, but *which* group lands in which stage is fixed:
stage shifts start at zero and walk one Gray code.  A stage costs its longest
host chain, so with a sparse spectrum the fixed assignment repeatedly pays for
one heavy group per stage while five hosts idle.

The same host algebra admits a free choice of the initial shift per output and of
the walk direction, which permutes the groups across stages without changing the
three-layer transitions.  Clustering the heavy groups into fewer stages then
lowers the sum of per-stage maxima.  This module enumerates that freedom
together with the ordered high/low split and emits the best assignment.
"""
import argparse
import itertools
import json
import math
import random
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile

from distributed_ucry import walsh, verify_component


def _walk_table():
    table = [(0, ())] * 256
    for bits in range(256):
        masks = [m for m in range(8) if bits >> m & 1]
        if not masks:
            continue
        best = None
        for perm in itertools.permutations(masks):
            cost = cur = 0
            for m in perm:
                cost += (cur ^ m).bit_count()
                cur = m
            cost += cur.bit_count()
            if best is None or cost < best[0]:
                best = (cost, perm)
        table[bits] = best
    return table


WALK = _walk_table()
ORDERED_HIGH = [h for h in itertools.permutations(range(6), 3)]


def spectrum(code):
    tab = np.array([[math.pi * ((code[y] >> j) & 1) for y in range(64)] for j in range(3)])
    return walsh(tab), tab


def occupancy(co, high, low, tol=1e-12):
    """occ[output][high-mask] -> {low-mask: angle}."""
    occ = [[dict() for _ in range(8)] for _ in range(3)]
    for j in range(3):
        for m in range(64):
            a = float(co[j][m])
            if abs(a) <= tol:
                continue
            mh = sum(((m >> high[k]) & 1) << k for k in range(3))
            ml = sum(((m >> low[k]) & 1) << k for k in range(3))
            occ[j][mh][ml] = a
    return occ


def shift_walk(init, direction):
    """Four per-output shifts; consecutive stages differ by one high wire.

    Output i never moves along its own wire, so its four shifts run through all
    four cosets of {0, e_i} exactly as the fixed Gray walk does.
    """
    shifts = [list(init)]
    for step in range(3):
        c = (step + direction) % 2
        prev = shifts[-1]
        shifts.append([prev[i] ^ (1 << ((i + c + 1) % 3)) for i in range(3)])
    return shifts


def stage_groups(shifts_stage):
    """The six (output, high-mask) groups hosted in one stage."""
    return ([(i, shifts_stage[i] ^ (1 << i)) for i in range(3)]
            + [(i, shifts_stage[i]) for i in range(3)])


def assignment_cost(occ, shifts):
    total = 0
    for stage in range(4):
        chains = []
        for j, mh in stage_groups(shifts[stage]):
            bits = 0
            for ml in occ[j][mh]:
                bits |= 1 << ml
            chains.append(WALK[bits][0] + bits.bit_count())
        total += max(chains)
    return total


def plan(code, limit=6):
    co, _ = spectrum(code)
    results = []
    for high in ORDERED_HIGH:
        low = [i for i in range(6) if i not in high]
        for low_order in ((0, 1, 2),):
            occ = occupancy(co, high, [low[k] for k in low_order])
            for init in itertools.product(range(8), repeat=3):
                for direction in (0, 1):
                    shifts = shift_walk(init, direction)
                    seen = set()
                    for stage in range(4):
                        seen.update(stage_groups(shifts[stage]))
                    if len(seen) != 24:
                        continue
                    results.append((assignment_cost(occ, shifts), high,
                                    [low[k] for k in low_order], init, direction))
    results.sort(key=lambda r: r[0])
    out = []
    seen_keys = set()
    for r in results:
        key = (r[1], tuple(r[3]), r[4])
        if key in seen_keys:
            continue
        seen_keys.add(key)
        out.append(r)
        if len(out) >= limit:
            break
    return out


def sweep_candidates(entries, low_wires):
    """Shortest closed walks over the needed low masks, one per wire ordering.

    Different orderings toggle different low wires at the same step, so keeping
    several lets the interleaver avoid control contention between hosts.
    """
    if not entries:
        return [[]]
    best = None
    out = []
    for order in itertools.permutations(range(3)):
        walk = [sum((((j ^ (j >> 1)) >> k) & 1) << order[k] for k in range(3)) for j in range(8)]
        selected = [m for m in walk if m in entries]
        for sequence in (selected, list(reversed(selected))):
            ops = []
            cur = 0
            for mask in sequence:
                for k in order:
                    if (cur ^ mask) >> k & 1:
                        ops.append(('cx', low_wires[k]))
                ops.append(('rz', entries[mask]))
                cur = mask
            for k in order:
                if cur >> k & 1:
                    ops.append(('cx', low_wires[k]))
            if best is None or len(ops) < best:
                best = len(ops)
            out.append(ops)
    shortest = [o for o in out if len(o) == best]
    return shortest


def interleave(qc, jobs, hosts, rng):
    pos = [0] * len(jobs)
    while any(pos[i] < len(jobs[i]) for i in range(len(jobs))):
        used = set()
        ready = [i for i in range(len(jobs)) if pos[i] < len(jobs[i])]
        rng.shuffle(ready)
        ready.sort(key=lambda i: len(jobs[i]) - pos[i], reverse=True)
        for i in ready:
            kind, value = jobs[i][pos[i]]
            if hosts[i] in used:
                continue
            if kind == 'cx':
                if value in used:
                    continue
                qc.cx(value, hosts[i])
                used.add(value)
            else:
                qc.rz(value, hosts[i])
            used.add(hosts[i])
            pos[i] += 1


def build(code, high, low, init, direction, seed=0,
          controls=tuple(range(6)), outputs=(6, 7, 8)):
    rng = random.Random(seed)
    co, _ = spectrum(code)
    occ = occupancy(co, high, low)
    shifts = shift_walk(init, direction)
    high_wires = [controls[h] for h in high]
    low_wires = [controls[l] for l in low]
    qc = QuantumCircuit(max(list(outputs) + list(controls)) + 1)
    for t in outputs:
        qc.rx(math.pi / 2, t)
    # seed each output with its initial shift while the high wires are still pure
    for i in range(3):
        for k in range(3):
            if init[i] >> k & 1:
                qc.cx(high_wires[k], outputs[i])
    for i in range(3):
        qc.cx(outputs[i], high_wires[i])
    for stage in range(4):
        hosts = high_wires + list(outputs)
        jobs = [rng.choice(sweep_candidates(occ[j][mh], low_wires))
                for j, mh in stage_groups(shifts[stage])]
        interleave(qc, jobs, hosts, rng)
        for i in range(3):
            qc.cx(outputs[i], high_wires[i])
        target = shifts[stage + 1] if stage < 3 else [0, 0, 0]
        for i in range(3):
            delta = shifts[stage][i] ^ target[i]
            for k in range(3):
                if delta >> k & 1:
                    qc.cx(high_wires[k], outputs[i])
        if stage < 3:
            for i in range(3):
                qc.cx(outputs[i], high_wires[i])
    for t in outputs:
        qc.rx(-math.pi / 2, t)
    return qc


def best(code, configs=6, seeds=6, verify=True):
    out = None
    for cost, high, low, init, direction in plan(code, configs):
        for seed in range(seeds):
            raw = build(code, high, low, init, direction, seed)
            comp = transpile(raw, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                             optimization_level=3, seed_transpiler=0)
            key = (comp.depth(), comp.count_ops().get('cx', 0))
            if out is None or key < out[0]:
                out = (key, comp, dict(cost=cost, high=list(high), low=list(low),
                                       init=list(init), direction=direction, seed=seed))
    if verify:
        _, tab = spectrum(code)
        verify_component(out[1], tab)
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--record', type=Path, default=Path('artifacts/185/class_codes.json'))
    p.add_argument('--side', choices=['y', 'x'], default='y')
    p.add_argument('--configs', type=int, default=5)
    p.add_argument('--seeds', type=int, default=25)
    a = p.parse_args()
    import two_stage_oracle as ts
    from post258_two_stage_anf import decode
    rec = json.loads(a.record.read_text())
    lab = decode(rec['ylab'] if a.side == 'y' else rec['xlab'])
    cls = ts.ROWCLS if a.side == 'y' else ts.COLCLS
    mask = rec['ymask'] if a.side == 'y' else rec['xmask']
    code = [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]
    key, circuit, cfg = best(code, a.configs, a.seeds)
    print(json.dumps(dict(depth=key[0], cx=key[1], config=cfg)))
