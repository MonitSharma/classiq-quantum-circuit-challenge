"""Anneal the kernel's unreachable-entry fill to minimise its emitted depth.

The 8-bit kernel table is fixed on reachable code pairs and free elsewhere.
The emitted depth depends on the Walsh support of the integer lift of the ANF
term set, which the free entries control.  The control is the protected label
set, whose recorded recipe has 69 Walsh masks and 38 native layers.
"""
from __future__ import annotations
import hashlib, json, math, random, sys, time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
import two_stage_oracle as ts
from distributed_frame_search import native
from post218_beam_phase import psynth
from post258_two_stage_anf import decode

KW = [11, 12, 13, 14, 4, 15, 16, 17]


def walsh2(a):
    a = np.atleast_2d(np.asarray(a, float)).copy()
    n = a.shape[1]
    h = 1
    while h < n:
        for i in range(0, n, 2 * h):
            lo = a[:, i:i+h].copy(); hi = a[:, i+h:i+2*h].copy()
            a[:, i:i+h] = lo + hi; a[:, i+h:i+2*h] = lo - hi
        h *= 2
    return a / n


def anf_of(table):
    a = table[:]
    for i in range(8):
        for m in range(256):
            if m >> i & 1:
                a[m] ^= a[m ^ (1 << i)]
    return a


def support_of(table):
    a = anf_of(table)
    terms = [m for m in range(1, 256) if a[m]]
    lifted = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], float)
    co = walsh2(math.pi * lifted)[0]
    return int(np.sum(np.abs(co[1:]) > 1e-12)), terms, co


def emit(co, seeds=(209, 1, 2, 3, 4, 5, 6, 7), beams=(64, 128)):
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    best = None
    for beam in beams:
        for s in seeds:
            try:
                k = native(psynth(8, targets, global_phase=float(co[0]), seed=s, beam=beam,
                                  branch=14, alpha=5.0, timew=0.3))
            except Exception:
                continue
            if best is None or (k.depth(), k.size()) < (best.depth(), best.size()):
                best = k
    return best


def codes_for(ylab, xlab):
    ycode = [((v & 32).bit_count() % 2) | (ylab[((v & 32).bit_count() % 2, c)] << 1)
             for v, c in enumerate(ts.ROWCLS)]
    xcode = [((v & 48).bit_count() % 2) | (xlab[((v & 48).bit_count() % 2, c)] << 1)
             for v, c in enumerate(ts.COLCLS)]
    return ycode, xcode


def table_for(ylab, xlab, fill=0):
    ycode, xcode = codes_for(ylab, xlab)
    fixed = {}
    for y in range(64):
        for x in range(64):
            w = ycode[y] | (xcode[x] << 4)
            b = int(ts.logo(x, y))
            assert fixed.setdefault(w, b) == b, 'inconsistent code'
    tab = [fixed.get(w, fill) for w in range(256)]
    return tab, fixed


def anneal(tab, fixed, seconds, seed=0):
    rng = random.Random(seed)
    free = [w for w in range(256) if w not in fixed]
    cur = tab[:]
    cs, _, _ = support_of(cur)
    best, besttab = cs, cur[:]
    t0 = time.time()
    while time.time() - t0 < seconds:
        w = rng.choice(free)
        cur[w] ^= 1
        s, _, _ = support_of(cur)
        if s <= cs or rng.random() < math.exp((cs - s) / max(2.0, 0.10 * cs)):
            cs = s
            if s < best:
                best, besttab = s, cur[:]
        else:
            cur[w] ^= 1
    return best, besttab


def main(labels_json, outdir, seconds=90):
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    rec = json.loads(Path(labels_json).read_text())
    ylab, xlab = decode(rec['ylab']), decode(rec['xlab'])
    tab, fixed = table_for(ylab, xlab)
    s0, t0, _ = support_of(tab)
    print('base (fill=0) masks', s0, 'anf terms', len(t0), 'reachable', len(fixed), flush=True)
    rows = []
    for seed in range(3):
        s, bt = anneal(tab, fixed, seconds, seed)
        print(f'  anneal seed {seed}: masks {s}', flush=True)
        _, terms, co = support_of(bt)
        k = emit(co)
        rows.append(dict(seed=seed, masks=s, anf=len(terms), depth=k.depth(),
                         cx=k.count_ops().get('cx', 0)))
        print('   ', rows[-1], flush=True)
        (outdir / f'kernel_s{seed}.qasm').write_text(qasm2.dumps(k))
    rows.sort(key=lambda r: (r['depth'], r['cx']))
    (outdir / 'report.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 90)
