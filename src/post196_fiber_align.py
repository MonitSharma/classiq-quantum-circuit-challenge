"""Align the two raw fibres so a five-address lookup keeps a four-bit descriptor.

The descriptor stays `(raw wire, three loaded bits)` and the kernel keeps its
eight wires, but the lookup reads only the five non-raw wires.  That works iff a
single code partition of the 32 addresses, with at most eight blocks, refines the
class partition of *both* raw fibres -- and which addresses of one fibre line up
with which of the other is ours to choose, via a raw-controlled map applied
before the lookup and undone by the oracle's own inverse.

A raw-controlled CNOT between two address wires is one Toffoli; a raw-controlled
X on an address wire is one CX.  So the search is over short products of those,
scored by the resulting block count.
"""
import argparse
import itertools
import json
from pathlib import Path

PAIRS = [(a, b) for a in range(5) for b in range(5) if a != b]


def fibres(classes, raw_wire):
    low = [i for i in range(6) if i != raw_wire]

    def addr(v):
        return sum(((v >> b) & 1) << k for k, b in enumerate(low))
    f0 = [None] * 32
    f1 = [None] * 32
    for v in range(64):
        if (v >> raw_wire) & 1:
            f1[addr(v)] = classes[v]
        else:
            f0[addr(v)] = classes[v]
    assert None not in f0 and None not in f1
    return f0, f1


def apply_linear(ops, a):
    bits = [(a >> i) & 1 for i in range(5)]
    for src, dst in ops:
        bits[dst] ^= bits[src]
    return sum(b << i for i, b in enumerate(bits))


def blocks(f0, f1, ops, shift):
    """Distinct (class in fibre 0, class in fibre 1) pairs after the alignment."""
    seen = set()
    for a in range(32):
        moved = apply_linear(ops, a) ^ shift
        seen.add((f0[moved], f1[a]))
    return len(seen)


def search(classes, raw_wire, max_ops, target):
    f0, f1 = fibres(classes, raw_wire)
    best = None
    for k in range(max_ops + 1):
        for ops in itertools.product(PAIRS, repeat=k):
            for shift in range(32):
                n = blocks(f0, f1, ops, shift)
                cost = 3 * len(ops) + bin(shift).count('1')
                if n <= target and (best is None or cost < best[0]):
                    best = (cost, n, list(ops), shift)
            if best is not None and k and best[0] <= 3 * k:
                break
        if best is not None:
            return best
    return best


def code_table(classes, raw_wire, ops, shift):
    """Three-bit code per address, shared by both fibres, plus the class map."""
    f0, f1 = fibres(classes, raw_wire)
    labels, code = {}, [0] * 32
    for a in range(32):
        moved = apply_linear(ops, a) ^ shift
        key = (f0[moved], f1[a])
        if key not in labels:
            labels[key] = len(labels)
        code[a] = labels[key]
    assert len(labels) <= 8, len(labels)
    return code, {f"{k[0]},{k[1]}": v for k, v in labels.items()}


def run(outdir, max_ops, target):
    from two_stage_oracle import ROWCLS, COLCLS
    outdir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, classes in (('y', ROWCLS), ('x', COLCLS)):
        best = None
        for raw in range(6):
            got = search(classes, raw, max_ops, target)
            if got and (best is None or got[0] < best[0]):
                best = got + (raw,)
        if best is None:
            print(name, 'no alignment within', target, 'blocks', flush=True)
            report[name] = None
            continue
        cost, n, ops, shift, raw = best
        code, labels = code_table(classes, raw, [tuple(o) for o in ops], shift)
        report[name] = dict(raw_wire=raw, ops=[list(o) for o in ops], shift=shift,
                            blocks=n, align_cost=cost, code=code, labels=labels)
        print(name, 'raw wire', raw, 'blocks', n, 'controlled ops', len(ops),
              'shift', shift, 'approx align depth', cost, flush=True)
    (outdir / 'align.json').write_text(json.dumps(report, indent=1) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--max-ops', type=int, default=3)
    p.add_argument('--target', type=int, default=8)
    a = p.parse_args()
    run(a.outdir, a.max_ops, a.target)
