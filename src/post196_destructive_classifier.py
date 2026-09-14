"""Search a destructive reversible classifier, which the 77-layer bound misses.

The loader floor of 77 derived elsewhere in this repository applies to the
*lookup* family: a controlled-Ry network whose every Walsh parity carries exactly
one output variable, so the wires holding pure coordinate parities cannot host
rotations.  A classifier is not that object.  For one coordinate side the oracle
only needs

    |z> |000>  ->  e^{i phi(z)} |anything injective(z)>

with four designated wires carrying a descriptor that determines the row (or
column) class.  The other five outputs are unconstrained, the coordinate need not
survive the computation, and nothing has to behave like a lookup on arbitrary
ancilla inputs -- the oracle's own `C^dagger K C` sandwich restores everything
and cancels the relative phases of RCCX gates, because `K` is diagonal.

So this searches classical reversible circuits directly: CX and relative-phase
Toffoli, scored by whether any four wires separate the classes.  Bit values are
simulated exactly as 64-bit truth tables, one per wire.
"""
import argparse
import itertools
import json
import random
from pathlib import Path

FULL = (1 << 64) - 1
QUADS = list(itertools.combinations(range(9), 4))


def class_pairs(classes):
    """Kept for reporting: how many input pairs a descriptor must separate."""
    return [(a, b) for a in range(64) for b in range(a + 1, 64)
            if classes[a] != classes[b]]


def conflicts(values, quad, classes, cutoff=None):
    """Class-distinct pairs sharing a signature, counted by grouping not pairing."""
    groups = {}
    v0, v1, v2, v3 = (values[w] for w in quad)
    for z in range(64):
        sig = (((v0 >> z) & 1) | (((v1 >> z) & 1) << 1)
               | (((v2 >> z) & 1) << 2) | (((v3 >> z) & 1) << 3))
        groups.setdefault(sig, []).append(classes[z])
    bad = 0
    for members in groups.values():
        n = len(members)
        if n < 2:
            continue
        counts = {}
        for c in members:
            counts[c] = counts.get(c, 0) + 1
        bad += n * (n - 1) // 2 - sum(k * (k - 1) // 2 for k in counts.values())
        if cutoff is not None and bad >= cutoff:
            return bad
    return bad


def score(values, classes):
    best = None
    for quad in QUADS:
        bad = conflicts(values, quad, classes, None if best is None else best[0] + 1)
        if best is None or bad < best[0]:
            best = (bad, quad)
            if bad == 0:
                break
    return best


def initial():
    values = [0] * 9
    for bit in range(6):
        values[bit] = sum(1 << z for z in range(64) if (z >> bit) & 1)
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


def candidates():
    out = [('cx', a, b) for a in range(9) for b in range(9) if a != b]
    out += [('ccx', a, b, c) for a, b in itertools.combinations(range(9), 2)
            for c in range(9) if c != a and c != b]
    return out


GATES = candidates()


def search(classes, beam, steps, seed, limit):
    rng = random.Random(seed)
    start = (initial(), (0,) * 9, ())
    frontier = [start]
    best = None
    for step in range(steps):
        pool = []
        for values, times, ops in frontier:
            for gate in GATES:
                nv, nt = apply_gate(values, times, gate)
                if nv == list(values):
                    continue
                pool.append((nv, tuple(nt), ops + (gate,)))
        scored = []
        seen = set()
        for nv, nt, ops in pool:
            key = tuple(nv)
            if key in seen:
                continue
            seen.add(key)
            bad, quad = score(nv, classes)
            scored.append((bad, max(nt), rng.random(), nv, nt, ops, quad))
        scored.sort(key=lambda r: (r[0], r[1], r[2]))
        frontier = [(r[3], r[4], r[5]) for r in scored[:beam]]
        top = scored[0]
        if best is None or (top[0], top[1]) < (best[0], best[1]):
            best = (top[0], top[1], top[5], top[6])
            print(dict(step=step, conflicts=top[0], depth=top[1], gates=len(top[5])), flush=True)
        if top[0] == 0:
            return dict(found=True, depth=top[1], gates=[list(g) for g in top[5]],
                        quad=list(top[6]))
        if max(r[1] for r in scored[:1]) > limit:
            break
    return dict(found=False, best_conflicts=best[0], depth=best[1],
                gates=[list(g) for g in best[2]], quad=list(best[3]))


def run(outdir, side, beam, steps, seed, limit):
    from two_stage_oracle import ROWCLS, COLCLS
    outdir.mkdir(parents=True, exist_ok=True)
    classes = ROWCLS if side == 'y' else COLCLS
    report = search(classes, beam, steps, seed, limit)
    report['side'] = side
    (outdir / f'classifier_{side}_seed{seed}.json').write_text(json.dumps(report, indent=1) + '\n')
    print(side, 'found' if report['found'] else 'not found',
          'depth', report['depth'], flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--side', choices=['y', 'x'], default='y')
    p.add_argument('--beam', type=int, default=24)
    p.add_argument('--steps', type=int, default=40)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--limit', type=int, default=90)
    a = p.parse_args()
    run(a.outdir, a.side, a.beam, a.steps, a.seed, a.limit)
