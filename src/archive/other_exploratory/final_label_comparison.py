"""Final measured comparison: complete native oracle depth for label sets.

Assembles relative-phase lookups for both axes with the kernel rebuilt from
post258_raw_parity_codes.poly, and reports the real u3/cx depth of the whole
18-wire circuit.  Also measures the protected label set against the RECORDED
38-layer kernel artifact to calibrate the pipeline against 186.
"""
from __future__ import annotations
import json, math, sys, time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2

import two_stage_oracle as ts
from post185_schedule_floor import anneal, support, kernel_masks
from post258_raw_parity_codes import cells, poly
from post258_two_stage_anf import ORDER, encode, decode
from post224_relative_lookup import relative
from depth_parity_network import walsh
from post218_beam_phase import psynth
from distributed_frame_search import native

KW = [11, 12, 13, 14, 4, 15, 16, 17]


def kernel_from_terms(terms, beams):
    lifted = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], float)
    co = walsh(math.pi * lifted)
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    best = None
    for bc in beams:
        try:
            k = native(psynth(8, targets, global_phase=float(co[0]), **bc))
        except Exception:
            continue
        if best is None or (k.depth(), k.size()) < (best[0].depth(), best[0].size()):
            best = (k, bc)
    return best[0], len(targets)


def encoders(ylab, xlab, xmask, ymask=32, seeds=range(16)):
    out = []
    for cls, mask, lab in ((ts.ROWCLS, ymask, ylab), (ts.COLCLS, xmask, xlab)):
        code = [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]
        tab = np.array([[math.pi * (c >> b & 1) for c in code] for b in range(3)])
        best = None
        for s in seeds:
            e, _ = relative(tab, s)
            if mask == xmask and cls is ts.COLCLS:
                e = e.copy(); e.cx(5, 4)
            if best is None or (e.depth(), e.size()) < (best.depth(), best.size()):
                best = e
        out.append(best)
    return out


def assemble(ey, ex, kern):
    enc = QuantumCircuit(18)
    enc.compose(ey, ts.YW + ts.YA, inplace=True)
    enc.compose(ex, ts.XW + ts.XA, inplace=True)
    return native(enc.compose(kern, KW).compose(enc.inverse()))


def main():
    beams = [dict(seed=s, beam=b, branch=br, alpha=a, timew=t)
             for s in (209, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
             for b in (64, 128, 256) for br in (14, 24) for a in (5.0, 8.0) for t in (0.3,)]
    base = json.loads(Path('artifacts/185/class_codes.json').read_text())
    ylab0, xlab0 = decode(base['ylab']), decode(base['xlab'])
    # calibration: protected labels, RECORDED kernel artifact
    ey, ex = encoders(ylab0, xlab0, 48)
    rec_kern = native(qasm2.load('artifacts/185/kernel.qasm'))
    q = assemble(ey, ex, rec_kern)
    print('CALIBRATION protected labels + recorded kernel:',
          dict(depth=q.depth(), cx=q.count_ops().get('cx', 0)), flush=True)

    # protected labels, poly kernel through the same emitter as the rest
    ycell, xcell = cells(ts.ROWCLS, 32), cells(ts.COLCLS, 48)
    terms0 = [m for i, m in enumerate(ORDER) if poly(ylab0, xlab0, ycell, xcell) >> i & 1]
    k0, m0 = kernel_from_terms(terms0, beams)
    q0 = assemble(*encoders(ylab0, xlab0, 48), k0)
    print('protected labels + poly kernel:', dict(masks=m0, kernel=k0.depth(),
                                                 depth=q0.depth(),
                                                 cx=q0.count_ops().get('cx', 0)), flush=True)

    rows = [dict(tag='protected', S=[support(ylab0, ts.ROWCLS, 32), support(xlab0, ts.COLCLS, 48)],
                 masks=m0, kernel=k0.depth(), depth=q0.depth(), cx=q0.count_ops().get('cx', 0))]
    start = time.time()
    for xmask in (16, 48):
        for seed in range(4):
            if time.time() - start > 420:
                break
            ymask = 32
            ycell, xcell = cells(ts.ROWCLS, ymask), cells(ts.COLCLS, xmask)
            value, rec = anneal(xmask, seed, 3000)
            if rec is None:
                continue
            ylab, xlab = decode(rec['ylab']), decode(rec['xlab'])
            Sy = support(ylab, ts.ROWCLS, ymask); Sx = support(xlab, ts.COLCLS, xmask)
            kern, nm = kernel_from_terms(rec['terms'], beams)
            q = assemble(*encoders(ylab, xlab, xmask), kern)
            row = dict(tag=f'x{xmask}s{seed}', floor=round(value, 1), S=[Sy, Sx], masks=nm,
                       kernel=kern.depth(), depth=q.depth(), cx=q.count_ops().get('cx', 0))
            rows.append(row)
            print(' ', row, flush=True)
        if time.time() - start > 420:
            break
    Path('artifacts/joint_floor_v2_report.json').write_text(json.dumps(rows, indent=2) + '\n')
    for r in rows:
        print('RESULT', r, flush=True)


if __name__ == '__main__':
    main()
