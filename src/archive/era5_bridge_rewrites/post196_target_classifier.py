"""Destructive classifier search with a smooth objective: distance to a target code.

Scoring a partial circuit by "do any four wires already separate the classes"
is a flat landscape -- a beam stalls around 25 unseparated pairs because most
single gates change nothing about separability.  Targeting a *specific*
class-determining descriptor instead gives a smooth objective: the Hamming
distance, over the 64 promised inputs, between each designated wire and the
function it should end up carrying.  Every gate moves it.

The descriptor is free, so any class-determining code will do; the target here is
the recorded code, and the search may destroy the coordinate wires because the
oracle's `C^dagger K C` sandwich restores them.
"""
import argparse
import itertools
import json
import random
from pathlib import Path

import numpy as np


def truth(bits):
    return sum(1 << z for z in range(64) if bits[z])


def initial():
    values = [0] * 9
    for bit in range(6):
        values[bit] = truth([(z >> bit) & 1 for z in range(64)])
    return values


def apply_gate(values, times, gate):
    values = list(values)
    times = list(times)
    if gate[0] == 'cx':
        _, a, b = gate
        values[b] ^= values[a]
        moment = max(times[a], times[b]) + 1
        times[a] = times[b] = moment
    else:
        _, a, b, c = gate
        values[c] ^= values[a] & values[b]
        moment = max(times[a], times[b], times[c]) + 3
        times[a] = times[b] = times[c] = moment
    return values, times


GATES = [('cx', a, b) for a in range(9) for b in range(9) if a != b]
GATES += [('ccx', a, b, c) for a, b in itertools.combinations(range(9), 2)
          for c in range(9) if c != a and c != b]


def distance(values, targets, slots):
    return sum(bin(values[w] ^ t).count('1') for w, t in zip(slots, targets))


def separates(values, slots, classes):
    seen = {}
    for z in range(64):
        sig = tuple((values[w] >> z) & 1 for w in slots)
        if seen.setdefault(sig, classes[z]) != classes[z]:
            return False
    return True


def search(targets, slots, classes, beam, steps, seed, noise=0.0):
    rng = random.Random(seed)
    frontier = [(initial(), (0,) * 9, ())]
    best = None
    for step in range(steps):
        pool, seen = [], set()
        for values, times, ops in frontier:
            for gate in GATES:
                nv, nt = apply_gate(values, times, gate)
                key = tuple(nv)
                if key in seen or nv == list(values):
                    continue
                seen.add(key)
                pool.append((nv, tuple(nt), ops + (gate,)))
        scored = []
        for nv, nt, ops in pool:
            d = distance(nv, targets, slots)
            # noise breaks the plateau where no single gate reduces the distance
            jitter = rng.random() * noise
            scored.append((d + jitter, d, max(nt), rng.random(), nv, nt, ops))
        scored.sort(key=lambda r: (r[0], r[2], r[3]))
        frontier = [(r[4], r[5], r[6]) for r in scored[:beam]]
        top = min(scored, key=lambda r: (r[1], r[2]))
        if best is None or (top[1], top[2]) < (best[0], best[1]):
            best = (top[1], top[2], top[6])
            print(dict(step=step, distance=top[1], depth=top[2], gates=len(top[6])),
                  flush=True)
        if top[1] == 0:
            ok = separates(top[4], slots, classes)
            return dict(found=True, depth=top[2], gates=[list(g) for g in top[6]],
                        separates=ok)
    return dict(found=False, best_distance=best[0], depth=best[1],
                gates=[list(g) for g in best[2]])


def affine_target(code, rows, shift):
    """Any invertible affine image of the code still determines the class."""
    out = []
    for z in range(64):
        value = 0
        for j in range(3):
            bit = (rows[j] & code[z]).bit_count() & 1
            bit ^= (shift >> j) & 1
            value |= bit << j
        out.append(value)
    return out


def run(outdir, side, beam, steps, seed, noise=0.0, variant=0):
    from two_stage_oracle import ROWCLS, COLCLS
    from post258_two_stage_anf import decode
    outdir.mkdir(parents=True, exist_ok=True)
    record = json.loads(Path('artifacts/218/class_codes.json').read_text())
    if side == 'y':
        classes, rho, labels = ROWCLS, 32, decode(record['ylab'])
    else:
        classes, rho, labels = COLCLS, 48, decode(record['xlab'])
    code = [labels[((z & rho).bit_count() & 1, classes[z])] for z in range(64)]
    if variant:
        maps = [rows for rows in itertools.product(range(8), repeat=3)
                if len({0, rows[0], rows[1], rows[2], rows[0] ^ rows[1],
                        rows[0] ^ rows[2], rows[1] ^ rows[2],
                        rows[0] ^ rows[1] ^ rows[2]}) == 8]
        rows = maps[variant % len(maps)]
        code = affine_target(code, rows, (variant // len(maps)) % 8)
    targets = [truth([(code[z] >> j) & 1 for z in range(64)]) for j in range(3)]
    slots = [6, 7, 8]
    report = search(targets, slots, classes, beam, steps, seed, noise)
    report.update(side=side, slots=slots)
    (outdir / f'target_{side}_seed{seed}.json').write_text(json.dumps(report, indent=1) + '\n')
    print(side, 'found' if report['found'] else 'not found', 'depth', report['depth'], flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--side', choices=['y', 'x'], default='y')
    p.add_argument('--beam', type=int, default=24)
    p.add_argument('--steps', type=int, default=60)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--noise', type=float, default=0.0)
    p.add_argument('--variant', type=int, default=0)
    a = p.parse_args()
    run(a.outdir, a.side, a.beam, a.steps, a.seed, a.noise, a.variant)
