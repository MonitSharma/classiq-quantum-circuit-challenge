"""Label annealing against the SPARSE parity-sweep emitter, scored by measured depth.

The protected labels have Walsh supports (47,64,64)/(46,64,64): two bits of odd
weight force all 192 rotations, so the sparse emitter has nothing to skip.
Labels of even weight admit sparse spectra, which emit_sparse_sweeps can
schedule with far fewer rotations.  This searches that space and scores the
COMPLETE oracle depth, never a proxy.
"""
from __future__ import annotations
import hashlib, itertools, json, math, random, sys, time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
import two_stage_oracle as ts
from distributed_ucry import structured_ucry
from distributed_frame_search import native
from post218_beam_phase import psynth

KW = [11, 12, 13, 14, 4, 15, 16, 17]


def walsh(tables):
    """Row-wise Walsh-Hadamard, normalised; handles 2-D tables."""
    a = np.atleast_2d(np.asarray(tables, float)).copy()
    h = 1
    n = a.shape[1]
    while h < n:
        for i in range(0, n, 2 * h):
            lo = a[:, i:i+h].copy()
            hi = a[:, i+h:i+2*h].copy()
            a[:, i:i+h] = lo + hi
            a[:, i+h:i+2*h] = lo - hi
        h *= 2
    return a / n


def cells(side):
    cls, mask = (ts.ROWCLS, 32) if side == 'y' else (ts.COLCLS, 48)
    return cls, mask, sorted({((v & mask).bit_count() % 2, c) for v, c in enumerate(cls)})


def code_of(side, lab):
    cls, mask, _ = cells(side)
    return [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]


def support(lab, side):
    code = code_of(side, lab)
    tab = np.array([[math.pi * (c >> b & 1) for c in code] for b in range(3)])
    co = walsh(tab)
    return int(np.sum(np.abs(co[:, 1:]) > 1e-12)), tab


def random_label(side, rng):
    cls, mask, cl = cells(side)
    lab = {}
    for v in (0, 1):
        group = [c for (p, c) in cl if p == v]
        vals = rng.sample(range(8), len(group))
        for c, val in zip(group, vals):
            lab[(v, c)] = val
    return lab


def anneal(side, seconds, seed):
    rng = random.Random(seed)
    lab = random_label(side, rng)
    cur = support(lab, side)[0]
    best, bestlab = cur, dict(lab)
    start = time.time()
    while time.time() - start < seconds:
        cls, mask, cl = cells(side)
        v = rng.randrange(2)
        group = [c for (p, c) in cl if p == v]
        if len(group) < 2:
            continue
        a, b = rng.sample(group, 2)
        lab[(v, a)], lab[(v, b)] = lab[(v, b)], lab[(v, a)]
        new = support(lab, side)[0]
        if new <= cur or rng.random() < math.exp((cur - new) / max(1.0, 0.15 * cur)):
            cur = new
            if new < best:
                best, bestlab = new, dict(lab)
        else:
            lab[(v, a)], lab[(v, b)] = lab[(v, b)], lab[(v, a)]
    return best, bestlab


def emit_loader(side, lab, budget=40):
    _, tab = support(lab, side)
    best = None
    for seed in range(12):
        for sparse, ow in ((True, False), (False, True)):
            try:
                raw = structured_ucry(tab, [6, 7, 8], list(range(6)), seed,
                                      sparse=sparse, open_walk=ow)
                q = native(raw)
            except Exception:
                continue
            sc = (q.depth(), q.count_ops().get('cx', 0))
            if best is None or sc < best[0]:
                best = (sc, dict(seed=seed, sparse=sparse, opened=ow), q)
    return best


def main(outdir, seconds=1200):
    outdir = Path(outdir)
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    rows = {}
    for side in ('x', 'y'):
        base = json.loads(Path('artifacts/185/class_codes.json').read_text())
        from post258_two_stage_anf import decode
        lab0 = decode(base[side + 'lab'])
        print(side, 'protected support', support(lab0, side)[0], flush=True)
        cands = [(support(lab0, side)[0], lab0, 'protected')]
        for seed in range(6):
            t0 = time.time()
            s, lab = anneal(side, seconds / 12, seed)
            print(f'  anneal seed {seed}: support {s} in {time.time()-t0:.0f}s', flush=True)
            cands.append((s, lab, f'anneal{seed}'))
        cands.sort(key=lambda r: r[0])
        seen, measured = set(), []
        for s, lab, tag in cands[:5]:
            key = tuple(sorted(lab.items()))
            if key in seen:
                continue
            seen.add(key)
            r = emit_loader(side, lab)
            measured.append((r[0][0], r[0][1], s, tag, r[1], lab))
            print(f'  {tag}: walsh {s} -> loader {r[0]} via {r[1]}', flush=True)
        measured.sort(key=lambda r: (r[0], r[1]))
        deps, cxs, s, tag, meta, lab = measured[0]
        rows[side] = dict(lab={f'{k[0]},{k[1]}': v for k, v in lab.items()}, walsh=s, tag=tag,
                          loader_depth=deps, loader_cx=cxs, meta=meta)
        print(side, 'BEST loader', deps, cxs, 'walsh', s, tag, meta, flush=True)
    (outdir / 'loaders.json').write_text(json.dumps(rows, indent=2) + '\n')

    from post258_two_stage_anf import decode as dec
    ylab = {tuple(int(t) for t in k.split(',')): v for k, v in rows['y']['lab'].items()}
    xlab = {tuple(int(t) for t in k.split(',')): v for k, v in rows['x']['lab'].items()}
    for fill in (0, 1):
        ycode = code_of('y', ylab)
        xcode = code_of('x', xlab)
        table = [fill] * 256
        cellsx = {}
        for x in range(64): cellsx.setdefault(xcode[x], []).append(x)
        cellsy = {}
        for y in range(64): cellsy.setdefault(ycode[y], []).append(y)
        for yv, ys in cellsy.items():
            for xv, xs in cellsx.items():
                bit = int(ts.logo(xs[0], ys[0]))
                assert all(int(ts.logo(a, b)) == bit for a in xs for b in ys)
                table[yv | (xv << 4)] = bit
        anf = table[:]
        for i in range(8):
            for m in range(256):
                if m >> i & 1:
                    anf[m] ^= anf[m ^ (1 << i)]
        terms = [m for m in range(1, 256) if anf[m]]
        lifted = np.array([sum(int(m & ~w == 0) for m in terms) for w in range(256)], float)
        co = walsh(math.pi * lifted)
        targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
        best = None
        for s in (209, 1, 2, 3, 4):
            k = native(psynth(8, targets, global_phase=float(co[0]), seed=s, beam=64,
                              branch=14, alpha=5.0, timew=0.35))
            if best is None or (k.depth(), k.size()) < (best.depth(), best.size()):
                best = k
        print('fill', fill, 'terms', len(terms), 'masks', len(targets), 'kernel', best.depth(),
              best.count_ops().get('cx', 0), flush=True)
    return rows


if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 1200)
