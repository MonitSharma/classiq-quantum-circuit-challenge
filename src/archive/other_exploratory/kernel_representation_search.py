"""Kernel representation search: choose the unreachable-code fill (and hence the
ANF lift) to minimise emitted kernel depth, and score the COMPLETE oracle.

The 8-bit kernel table is fixed on reachable (ycode,xcode) pairs and free on the
rest.  Different fills give different ANF term sets and different Walsh support,
so the emitted depth is not determined by the target function alone.
"""
from __future__ import annotations
import hashlib, json, math, random, sys, time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
import two_stage_oracle as ts
from distributed_frame_search import native
from post218_beam_phase import psynth
from depth_parity_network import walsh

KW = [11, 12, 13, 14, 4, 15, 16, 17]


def anf_terms(table):
    a = table[:]
    for i in range(8):
        for m in range(256):
            if m >> i & 1:
                a[m] ^= a[m ^ (1 << i)]
    return [m for m in range(1, 256) if a[m]]


def mask_count(terms):
    lifted = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], float)
    co = walsh(math.pi * lifted)
    return int(np.sum(np.abs(co[1:]) > 1e-12)), co


def emit(terms, seeds=(209, 1, 2, 3, 4, 5), beam=64, branch=14, alpha=5.0, timew=0.35):
    _, co = mask_count(terms)
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    best = None
    for s in seeds:
        try:
            k = native(psynth(8, targets, global_phase=float(co[0]), seed=s, beam=beam,
                              branch=branch, alpha=alpha, timew=timew))
        except Exception:
            continue
        if best is None or (k.depth(), k.size()) < (best.depth(), best.size()):
            best = k
    return best


def main(outdir):
    rec = json.loads(Path('artifacts/185/class_codes.json').read_text())
    from post258_two_stage_anf import decode
    ylab, xlab = decode(rec['ylab']), decode(rec['xlab'])
    # 4-bit code: raw coordinate wire (the free parity) plus the three loaded bits
    ycode = [((v & 32).bit_count() % 2) | (ylab[((v & 32).bit_count() % 2, c)] << 1)
             for v, c in enumerate(ts.ROWCLS)]
    xcode = [((v & 48).bit_count() % 2) | (xlab[((v & 48).bit_count() % 2, c)] << 1)
             for v, c in enumerate(ts.COLCLS)]
    fixed = {}
    for y in range(64):
        for x in range(64):
            w = ycode[y] | (xcode[x] << 4)
            b = int(ts.logo(x, y))
            assert fixed.setdefault(w, b) == b
    free = [w for w in range(256) if w not in fixed]
    print('reachable', len(fixed), 'free', len(free), flush=True)

    base = [fixed.get(w, 0) for w in range(256)]
    print('fill=0  terms', len(anf_terms(base)), 'masks', mask_count(anf_terms(base))[0], flush=True)
    alt = [fixed.get(w, 1) for w in range(256)]
    print('fill=1  terms', len(anf_terms(alt)), 'masks', mask_count(anf_terms(alt))[0], flush=True)

    rng = random.Random(7)
    cur = base[:]
    cterms = len(anf_terms(cur))
    best, besttab, bestterms = cterms, cur[:], anf_terms(cur)
    start = time.time()
    while time.time() - start < 120:
        w = rng.choice(free)
        cur[w] ^= 1
        t = len(anf_terms(cur))
        if t <= cterms or rng.random() < 0.02:
            cterms = t
            if t < best:
                best, besttab, bestterms = t, cur[:], anf_terms(cur)
        else:
            cur[w] ^= 1
    print('annealed ANF terms', best, 'masks', mask_count(bestterms)[0], flush=True)

    outdir = Path(outdir)
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    rows = []
    for tag, terms in (('fill0', anf_terms(base)), ('fill1', anf_terms(alt)), ('anneal', bestterms)):
        k = emit(terms)
        rows.append(dict(tag=tag, terms=len(terms), masks=mask_count(terms)[0],
                         depth=k.depth(), cx=k.count_ops().get('cx', 0)))
        print(rows[-1], flush=True)
        (outdir / f'kernel_{tag}.qasm').write_text(qasm2.dumps(k))
    t = anf_terms(bestterms)
    # also try much larger beams on the best representation
    for beam in (128, 256):
        k = emit(t, seeds=(209, 1, 2, 3, 4, 5, 6, 7), beam=beam, branch=20, alpha=8.0)
        rows.append(dict(tag=f'anneal_beam{beam}', terms=len(t), masks=mask_count(t)[0],
                         depth=k.depth(), cx=k.count_ops().get('cx', 0)))
        print(rows[-1], flush=True)
        (outdir / f'kernel_anneal_beam{beam}.qasm').write_text(qasm2.dumps(k))
    (outdir / 'report.json').write_text(json.dumps(rows, indent=2) + '\n')
    print('baseline recorded kernel artifacts/185/kernel.qasm = 38 layers / 87 CX', flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
