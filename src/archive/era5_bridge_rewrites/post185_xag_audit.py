"""Cost and width audit of the direct XAG phase-oracle route.

The leaderboard's top four entries sit at 343-561 CX, against our 854. Reading
those numbers as a relative-phase Toffoli compute/uncompute of an AND network,

    CX  ~  6 * (AND gates)  +  2 * (CX needed to assemble the affine operands)
    depth ~ 2 * (AND depth) * 7  +  routing

places every one of them in that regime and none of them in ours. This module
measures the repository's own exact XAG networks against that model, and
measures the one thing that keeps us out of it: width.

Width is hard-capped. Eighteen wires must still span the twelve coordinates at
every moment, because the circuit has to restore them, so at most **six** AND
values can be live at once. The exact networks here need fourteen to eighteen.

It also records the accounting error in `src/xag_to_inplace_layers.py`, whose
5,131-layer result is what closed this route before. That compiler pays for the
network four times over; see `cost_of_existing_compiler`.
"""
import argparse
import glob
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 13          # signal 0 is the constant, 1..12 the coordinates, 13+ the ANDs


def parse(path):
    ands, out = [], None
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        f = s.split()
        if f[0] == 'AND':
            ands.append((int(f[1]), int(f[2])))
        else:
            out = int(f[1])
    return ands, out


def signals(mask):
    out = []
    while mask:
        i = mask.bit_length() - 1
        mask ^= 1 << i
        out.append(i)
    return out


def is_exact(path):
    """Whether this file really implements the logo (two of them do not)."""
    from destructive_xag import load_xag
    try:
        load_xag(Path(path))
        return True
    except ValueError:
        return False


def cost_model(path):
    """AND count, AND depth, affine routing CX, and the implied total CX."""
    ands, out = parse(path)
    level = {i: 0 for i in range(BASE)}
    routing = 0
    for k, (a, b) in enumerate(ands):
        d = 0
        for mask in (a, b):
            sigs = signals(mask)
            for i in sigs:
                d = max(d, level.get(i, 0))
            # the constant is an X gate, every further term costs one CX
            routing += max(0, len(sigs) - 1 - (1 if mask & 1 else 0))
        level[BASE + k] = d + 1
    md = max(level.values())
    sizes = [sum(1 for v in range(BASE, BASE + len(ands)) if level[v] == L)
             for L in range(1, md + 1)]
    return dict(ands=len(ands), and_depth=md, level_sizes=sizes,
                routing_cx=routing, predicted_cx=6 * len(ands) + 2 * routing,
                output_terms=len(signals(out)))


def width_audit(path, restarts=200, seed=0):
    """Peak live AND values, phasing each output root the moment it exists.

    The output is an affine form, so the constant is a global phase, each linear
    term is a Z on a coordinate wire, and each AND root only needs a Z while it
    happens to be live. Nothing has to be accumulated into one bit, which is what
    the existing compiler does.
    """
    ands, out = parse(path)
    n = len(ands)
    deps = []
    for a, b in ands:
        s = set()
        for mask in (a, b):
            for i in signals(mask):
                if i >= BASE:
                    s.add(i - BASE)
        deps.append(s)
    consumers = [set() for _ in range(n)]
    for k, s in enumerate(deps):
        for u in s:
            consumers[u].add(k)
    rng = random.Random(seed)
    best = None
    for r in range(restarts):
        rng.seed(r)
        done, live, peak = set(), set(), 0
        pending = {k: set(consumers[k]) for k in range(n)}
        while len(done) < n:
            ready = [k for k in range(n) if k not in done and deps[k] <= done]
            scored = sorted((-sum(1 for u in deps[k] if pending[u] == {k}),
                             len(deps[k] - live), rng.random(), k) for k in ready)
            k = scored[0][3]
            done.add(k)
            if consumers[k]:
                live.add(k)
            for u in deps[k]:
                pending[u].discard(k)
            for u in list(live):
                if not pending[u]:
                    live.discard(u)
            peak = max(peak, len(live))
        best = peak if best is None else min(best, peak)
    return dict(peak_live_and_values=best, wires_needed=12 + best, wires_available=18)


def cost_of_existing_compiler(path):
    """How many times `xag_to_inplace_layers` evaluates the network.

    It pebbles each output root's cone from scratch, XORs the root into an
    accumulator wire and unpebbles the cone, then wraps the whole of that in
    `E -> Z -> E-dagger`. Cones overlap heavily, and the accumulator forces the
    second copy, so the network is walked far more than the twice a single
    shared pass would need.
    """
    ands, out = parse(path)
    n = len(ands)
    deps = []
    for a, b in ands:
        s = set()
        for mask in (a, b):
            for i in signals(mask):
                if i >= BASE:
                    s.add(i - BASE)
        deps.append(s)
    roots = [i - BASE for i in signals(out) if i >= BASE]

    def cone(r):
        seen, stack = set(), [r]
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            stack.extend(deps[v])
        return seen

    per_root = sum(len(cone(r)) for r in roots)
    return dict(roots=len(roots), and_gates=n,
                cone_evaluations_per_pass=per_root,
                shared_pass_evaluations=n,
                compute_uncompute_factor=2,
                existing_factor=4,
                ratio=round(2 * per_root / n, 2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dir', type=Path,
                   default=ROOT / 'artifacts/multiplicative_depth/optimized')
    a = p.parse_args()
    rows = []
    for path in sorted(glob.glob(str(a.dir / '*.xag'))):
        row = dict(name=Path(path).stem, exact=is_exact(path))
        row.update(cost_model(path))
        row.update(width_audit(path))
        row.update(cost_of_existing_compiler(path))
        rows.append(row)
        print(json.dumps(row))
