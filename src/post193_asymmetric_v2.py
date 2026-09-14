"""Asymmetric compute/uncompute loader pairs, against any packaged kernel.

`post193_asymmetric_loaders` is hardwired to the 193/855 kernel and compiled 600
of its candidate pairs.  The shipped oracle now uses a different kernel and
mapping, and the pair space is large, so this takes the kernel and mapping as
inputs and sweeps far more of it.

A forward and an inverse loader schedule may be combined without a phase
correction only when their input-dependent phases agree up to a global phase;
`gauge` computes that phase symbolically on all 64 coordinate values, and pairs
are formed only inside a gauge class.  The composed depth is predicted exactly
from the per-wire timing before any transpilation -- the assertion below checks
that -- so candidates can be ranked cheaply and only the best compiled.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2

import two_stage_oracle as ts
from build_two_stage_196 import KERNEL_WIRES
from distributed_frame_search import native
from post193_asymmetric_loaders import gauge
from post224_relative_lookup import relative
from post258_joint_encoder_schedule import touches
from post258_two_stage_anf import decode


def options(codes, seeds):
    bags = []
    for side, cls, key in [(0, ts.ROWCLS, 'ylab'), (1, ts.COLCLS, 'xlab')]:
        mask = codes['ymask'] if side == 0 else codes['xmask']
        lab = decode(codes[key])
        values = [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]
        table = math.pi * np.array([[v >> b & 1 for v in values] for b in range(3)])
        found = {}
        for seed in range(seeds):
            phase = gauge(table, values, seed)
            e, _ = relative(table, seed)
            if side:
                e.cx(5, 4)
            key2 = (phase, tuple(touches(e)))
            row = dict(seed=seed, times=tuple(touches(e)), phase=phase)
            if key2 not in found or e.size() < found[key2][0].size():
                found[key2] = (e, row)
        bags.append(list(found.values()))
        print('side', side, 'distinct schedules', len(bags[-1]),
              'gauge classes', len({m['phase'] for _, m in bags[-1]}), flush=True)
    return bags


def run(out, package, seeds, limit, baseline):
    assert not out.exists()
    out.mkdir(parents=True)
    codes = json.loads((package / 'class_codes.json').read_text())
    kernel = qasm2.load(package / 'kernel.qasm')
    mapping = json.loads((package / 'replay_recipe.json').read_text())['mapping']
    bags = options(codes, seeds)

    combos = []
    for ey, my in bags[0]:
        for ex, mx in bags[1]:
            times = tuple(mx['times'][:6] + my['times'][:6]
                          + my['times'][6:] + mx['times'][6:])
            combos.append((times, ey, ex, my, mx))
    by_gauge = {}
    for item in combos:
        by_gauge.setdefault((item[3]['phase'], item[4]['phase']), []).append(item)

    candidates = []
    for before, ey, ex, my, mx in combos:
        after = list(before)
        for w, t in zip(KERNEL_WIRES, touches(kernel, [before[w] for w in KERNEL_WIRES])):
            after[w] = t
        for tail, fy, fx, ny, nx in by_gauge[(my['phase'], mx['phase'])]:
            depth = max(tail[w] + after[mapping[w]] for w in range(18))
            size = ey.size() + ex.size() + fy.size() + fx.size()
            candidates.append((depth, size, ey, ex, fy, fx,
                               my['seed'], mx['seed'], ny['seed'], nx['seed']))
    spread = sorted({c[0] for c in candidates})
    print('pairs', len(candidates), 'predicted depths', spread[:6], flush=True)

    best = tuple(baseline)
    rows = []
    ordered = sorted(candidates, key=lambda c: c[:2])
    for predicted, _, ey, ex, fy, fx, ys, xs, yt, xt in ordered[:limit]:
        e, f = QuantumCircuit(18), QuantumCircuit(18)
        for circuit, y, x in ((e, ey, ex), (f, fy, fx)):
            circuit.compose(y, ts.YW + ts.YA, inplace=True)
            circuit.compose(x, ts.XW + ts.XA, inplace=True)
        raw = e.compose(kernel, KERNEL_WIRES).compose(f.inverse(), mapping)
        assert raw.depth() == predicted, (raw.depth(), predicted)
        q = native(raw)
        text = qasm2.dumps(q)
        q = qasm2.loads(text)
        score = (q.depth(), q.count_ops().get('cx', 0))
        rows.append(dict(depth=score[0], cx=score[1], predicted=predicted,
                         forward=[ys, xs], inverse=[yt, xt]))
        if score < best:
            best = score
            path = out / f'oracle_d{score[0]}_cx{score[1]}.qasm'
            path.write_text(text)
            from exhaustive_verify import exhaustive
            exhaustive(path)
            rows[-1]['path'] = str(path)
            print('IMPROVEMENT', rows[-1], flush=True)
        (out / 'report.json').write_text(json.dumps(
            dict(best=list(best), seeds=seeds, pairs=len(candidates),
                 compiled=len(rows), rows=rows[-400:]), indent=2))
    print('finished', best, 'compiled', len(rows), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--package', type=Path, default=Path('artifacts/193_cx853'))
    p.add_argument('--seeds', type=int, default=512)
    p.add_argument('--limit', type=int, default=3000)
    p.add_argument('--baseline', type=int, nargs=2, default=[193, 853])
    a = p.parse_args()
    run(a.outdir, a.package, a.seeds, a.limit, a.baseline)
