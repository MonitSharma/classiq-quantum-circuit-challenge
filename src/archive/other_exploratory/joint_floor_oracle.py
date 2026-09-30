"""Joint loader/kernel annealing scored by the COMPLETE emitted oracle depth.

Uses the repository's own annealer (post185_schedule_floor) to move labels on a
bound that combines loader Walsh support S with kernel integer-lift mask count M,
then rebuilds the kernel with post258_raw_parity_codes.poly and measures the
real native u3/cx depth of the whole oracle.  Nothing is promoted without the
full exhaustive verifier.
"""
from __future__ import annotations
import hashlib, json, math, sys, time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2

import two_stage_oracle as ts
from post185_schedule_floor import anneal, support, kernel_masks, floor_of
from post258_raw_parity_codes import cells, poly
from post258_two_stage_anf import ORDER, encode, decode
from post224_relative_lookup import relative
from depth_parity_network import walsh
from post218_beam_phase import psynth
from distributed_frame_search import native

KW = [11, 12, 13, 14, 4, 15, 16, 17]


def kernel_from_terms(terms, beams=None):
    lifted = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], float)
    co = walsh(math.pi * lifted)
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    beams = beams or [dict(seed=s, beam=b, branch=14, alpha=5.0, timew=0.3)
                      for s in (209, 1, 2, 3, 4, 5, 6, 7) for b in (64, 128)]
    best = None
    for bc in beams:
        try:
            k = native(psynth(8, targets, global_phase=float(co[0]), **bc))
        except Exception:
            continue
        if best is None or (k.depth(), k.size()) < (best[0].depth(), best[0].size()):
            best = (k, bc)
    return best[0], len(targets)


def encoders(ylab, xlab, seeds=range(16)):
    out = []
    for side, cls, mask, lab, wires in (('y', ts.ROWCLS, 32, ylab, ts.YW + ts.YA),
                                        ('x', ts.COLCLS, 48, xlab, ts.XW + ts.XA)):
        code = [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]
        tab = np.array([[math.pi * (c >> b & 1) for c in code] for b in range(3)])
        best = None
        for s in seeds:
            e, _ = relative(tab, s)
            if side == 'x':
                e = e.copy()
                e.cx(5, 4)
            if best is None or (e.depth(), e.size()) < (best.depth(), best.size()):
                best = e
        out.append(best)
    return out


def assemble(ey, ex, kern):
    enc = QuantumCircuit(18)
    enc.compose(ey, ts.YW + ts.YA, inplace=True)
    enc.compose(ex, ts.XW + ts.XA, inplace=True)
    return native(enc.compose(kern, KW).compose(enc.inverse()))


def main(outdir, anneal_seconds=300, target_steps=3000):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ycell, xcell = cells(ts.ROWCLS, 32), cells(ts.COLCLS, 48)
    records = []
    start = time.time()
    for xmask in (48, 6, 16, 60):
        for seed in range(3):
            if time.time() - start > anneal_seconds:
                break
            ycell, xcell = cells(ts.ROWCLS, 32), cells(ts.COLCLS, xmask)
            value, rec = anneal(xmask, seed, target_steps)
            if rec is None:
                continue
            rec['xmask_used'] = xmask
            records.append((value, rec))
            print(f'xmask {xmask} seed {seed}: floor {value:.1f} S={rec["S"]} M={rec["M"]}',
                  flush=True)
        if time.time() - start > anneal_seconds:
            break
    base = json.loads(Path('artifacts/185/class_codes.json').read_text())
    base_terms = base['terms']
    base_masks = kernel_masks(base_terms)
    s_y = support(decode(base['ylab']), ts.ROWCLS, 32)
    s_x = support(decode(base['xlab']), ts.COLCLS, 48)
    print(f'protected labels: S=({s_y},{s_x}) M={base_masks}', flush=True)

    cands = [dict(terms=base_terms, ylab=base['ylab'], xlab=base['xlab'], tag='protected')]
    records.sort(key=lambda r: r[0])
    for value, rec in records[:8]:
        cands.append(dict(terms=rec['terms'], ylab=rec['ylab'], xlab=rec['xlab'],
                          tag=f'anneal_x{rec["xmask_used"]}_s{rec["seed"]}_floor{value:.0f}'))

    results = []
    best = None
    for c in cands:
        try:
            ylab, xlab = decode(c['ylab']), decode(c['xlab'])
            ey, ex = encoders(ylab, xlab)
            kern, nmask = kernel_from_terms(c['terms'])
            q = assemble(ey, ex, kern)
        except Exception as exc:
            print('  skip', c['tag'], repr(exc)[:120], flush=True)
            continue
        row = dict(tag=c['tag'], encoder_y=ey.depth(), encoder_x=ex.depth(), kernel=kern.depth(),
                   masks=nmask, depth=q.depth(), cx=q.count_ops().get('cx', 0))
        results.append(row)
        print('  ', row, flush=True)
        key = (q.depth(), q.count_ops().get('cx', 0))
        if best is None or key < best[0]:
            best = (key, q, c, row)
            path = outdir / f'candidate_d{q.depth()}.qasm'
            path.write_text(qasm2.dumps(q))
            print('   NEW CANDIDATE', key, path, flush=True)
    (outdir / 'report.json').write_text(json.dumps(dict(rows=results, protected=[185, 854, 18]),
                                                   indent=2) + '\n')
    if best:
        print('FINAL', best[0], best[3], flush=True)
        return outdir / f'candidate_d{best[0][0]}.qasm'
    return None


if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 300)
