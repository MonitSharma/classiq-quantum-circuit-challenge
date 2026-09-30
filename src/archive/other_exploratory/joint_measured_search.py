"""Joint measured-depth search over the protected two-stage architecture.

Everything is scored by the depth of the COMPLETE native u3/cx oracle, not by
a proxy: encoder seed and high/low split, kernel beam schedule, and gate
order.  No proxy improvements are reported as results.
"""
from __future__ import annotations
import hashlib, itertools, json, math, sys, time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
import two_stage_oracle as ts
from distributed_ucry import structured_ucry
from distributed_frame_search import native
from depth_parity_network import walsh
from post218_beam_phase import psynth
from post258_two_stage_anf import decode

KW = [11, 12, 13, 14, 4, 15, 16, 17]


def table_of(codes):
    return np.array([[math.pi * (c >> b & 1) for c in codes] for b in range(3)])


def codes_of(side, lab):
    mask, cls = (32, ts.ROWCLS) if side == 'y' else (48, ts.COLCLS)
    return [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]


def relative_encoder(codes, seed, high=None, open_walk=True, sparse=False):
    """H-basis relative-phase lookup, matching artifacts/185 provenance."""
    tab = table_of(codes)
    q = structured_ucry(tab, [6, 7, 8], list(range(6)), seed,
                        high=high, sparse=sparse, open_walk=open_walk)
    data = list(q.data)
    assert all(i.operation.name == 'rx' for i in data[:3] + data[-3:])
    body = data[3:-3]
    while body and body[-1].operation.name == 'cx':
        inst = body[-1]
        a, b = [q.find_bit(v).index for v in inst.qubits]
        if a >= 6 or b < 6:
            break
        body.pop()
    out = QuantumCircuit(9)
    for b in (6, 7, 8):
        out.h(b)
    for inst in body:
        out.append(inst.operation, [q.find_bit(v).index for v in inst.qubits])
    for b in (6, 7, 8):
        out.h(b)
    return native(out)


def kernel_candidates(terms, fills=(0,), beams=None, seconds=60):
    beams = beams or [dict(seed=s, beam=b, branch=br, alpha=a, timew=t)
                      for s in (209, 1, 2, 3, 4)
                      for b in (32, 64, 128)
                      for br in (10, 14, 20)
                      for a in (3.0, 5.0, 8.0)
                      for t in (0.25, 0.35)]
    lifted = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], float)
    phases = math.pi * lifted
    co = walsh(phases)
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    print('kernel walsh masks', len(targets), flush=True)
    best = []
    start = time.time()
    for b in beams:
        if time.time() - start > seconds:
            break
        try:
            k = native(psynth(8, targets, global_phase=float(co[0]), **b))
        except Exception:
            continue
        best.append((k.depth(), k.count_ops().get('cx', 0), b, k))
    best.sort(key=lambda r: (r[0], r[1]))
    return best


def assemble(ey, ex, kern):
    enc = QuantumCircuit(18)
    enc.compose(ey, ts.YW + ts.YA, inplace=True)
    enc.compose(ex, ts.XW + ts.XA, inplace=True)
    q = native(enc.compose(kern, KW).compose(enc.inverse()))
    return q


def main(outdir, seconds=600):
    outdir = Path(outdir)
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    rec = json.loads(Path('artifacts/185/class_codes.json').read_text())
    ylab, xlab = decode(rec['ylab']), decode(rec['xlab'])
    yc, xc = codes_of('y', ylab), codes_of('x', xlab)

    enc_rows = []
    start = time.time()
    yopts, xopts = [], []
    for seed in range(48):
        if time.time() - start > seconds * 0.5:
            break
        for codes, store in ((yc, yopts), (xc, xopts)):
            try:
                e = relative_encoder(codes, seed)
            except Exception as exc:
                continue
            store.append((e.depth(), e.count_ops().get('cx', 0), seed, e))
        print('encoder seed', seed, 'y', yopts[-1][:3], 'x', xopts[-1][:3], flush=True)
    yopts.sort(key=lambda r: (r[0], r[1]))
    xopts.sort(key=lambda r: (r[0], r[1]))
    print('best encoders y', yopts[0][:3], 'x', xopts[0][:3], flush=True)

    kerns = kernel_candidates(rec['terms'], seconds=seconds * 0.5)
    print('best kernels', [(k[0], k[1], k[2]) for k in kerns[:5]], flush=True)
    if not kerns:
        return None

    best = None
    for (dy, cy, sy, ey) in yopts[:6]:
        for (dx, cx, sx, ex) in xopts[:6]:
            for (dk, ck, bk, kern) in kerns[:8]:
                q = assemble(ey, ex, kern)
                key = (q.depth(), q.count_ops().get('cx', 0))
                if best is None or key < best[0]:
                    best = (key, q, sy, sx, bk, dy, dx, dk)
                    print('new best', key, 'seeds', sy, sx, flush=True)
    key, q, sy, sx, bk, dy, dx, dk = best
    path = outdir / f'oracle_d{q.depth()}.qasm'
    path.write_text(qasm2.dumps(q))
    report = dict(depth=q.depth(), cx=q.count_ops().get('cx', 0), width=q.num_qubits,
                  sha256=hashlib.sha256(path.read_text().encode()).hexdigest(),
                  yseed=sy, xseed=sx, kernel_beam=bk, encoder_depth_y=dy, encoder_depth_x=dx,
                  kernel_depth=dk)
    (outdir / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    return path


if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 600)
