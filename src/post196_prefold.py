"""Find a cheap reversible pre-map that lets the lookup drop an address bit.

Measured lookup cost, three outputs, beam-scheduled and Rx-conjugated:
six address bits 77 layers, five 48, four 33.  The descriptor must stay four
bits or the kernel widens, so the only way to use a five-address lookup is for a
single eight-block code partition of the 32 addresses to refine the class
partition of *both* raw fibres.

Which addresses of one fibre face which of the other is set by a reversible map
applied before the lookup, and undone by the oracle's own inverse.  A map that is
*controlled* on the raw wire turns every CNOT into a Toffoli, and sampling shows
affine ones reach only 11-12 blocks.  An *uncontrolled* map on all six wires is
far cheaper per gate and rearranges fibres and addresses together, so that is
what is searched here.
"""
import argparse
import itertools
import json
import random
from collections import Counter
from pathlib import Path

GATES = [('cx', a, b) for a in range(6) for b in range(6) if a != b]
GATES += [('ccx', a, b, c) for a, b in itertools.combinations(range(6), 2)
          for c in range(6) if c not in (a, b)]
COST = {'cx': 1, 'ccx': 3}


def permute(ops):
    out = []
    for v in range(64):
        bits = [(v >> i) & 1 for i in range(6)]
        for op in ops:
            if op[0] == 'cx':
                bits[op[2]] ^= bits[op[1]]
            else:
                bits[op[3]] ^= bits[op[1]] & bits[op[2]]
        out.append(sum(b << i for i, b in enumerate(bits)))
    return out


def block_count(classes, perm, raw):
    """Distinct (fibre-0 class, fibre-1 class) pairs at each shared address."""
    low = [i for i in range(6) if i != raw]
    f0, f1 = {}, {}
    for v in range(64):
        w = perm[v]
        a = sum(((w >> b) & 1) << k for k, b in enumerate(low))
        (f1 if (w >> raw) & 1 else f0)[a] = classes[v]
    if len(f0) != 32 or len(f1) != 32:
        return None
    return len({(f0[a], f1[a]) for a in range(32)})


def search(classes, depth, tries, seed, target):
    rng = random.Random(seed)
    best = None
    for _ in range(tries):
        k = rng.randint(1, depth)
        ops = [rng.choice(GATES) for _ in range(k)]
        perm = permute(ops)
        if len(set(perm)) != 64:
            continue
        for raw in range(6):
            n = block_count(classes, perm, raw)
            if n is None or n > target:
                continue
            cost = sum(COST[o[0]] for o in ops)
            if best is None or cost < best[0]:
                best = (cost, n, raw, [list(o) for o in ops])
    return best


def run(outdir, depth, tries, seeds, target):
    from two_stage_oracle import ROWCLS, COLCLS
    outdir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, classes in (('y', ROWCLS), ('x', COLCLS)):
        best = None
        for s in range(seeds):
            got = search(classes, depth, tries, s, target)
            if got and (best is None or got[0] < best[0]):
                best = got
        if best is None:
            print(name, 'no pre-map within', target, 'blocks', flush=True)
            report[name] = None
        else:
            cost, n, raw, ops = best
            report[name] = dict(cost=cost, blocks=n, raw_wire=raw, ops=ops)
            print(name, 'blocks', n, 'raw wire', raw, 'gate cost', cost,
                  'ops', ops, flush=True)
    (outdir / 'prefold.json').write_text(json.dumps(report, indent=1) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--depth', type=int, default=5)
    p.add_argument('--tries', type=int, default=40000)
    p.add_argument('--seeds', type=int, default=4)
    p.add_argument('--target', type=int, default=8)
    a = p.parse_args()
    run(a.outdir, a.depth, a.tries, a.seeds, a.target)
