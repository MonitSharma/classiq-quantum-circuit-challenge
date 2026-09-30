"""Revisit five-variable labels using reachable-state kernel completion.

Two raw parities plus three loaded bits describe each axis. The loaded label
is constant along a nonzero translation direction. Search label assignments
jointly with a low-degree, integer-lifted phase kernel; score final circuits
by depth. No Boolean term count here is a circuit lower bound.
"""
import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator

from distributed_frame_search import native
from distributed_ucry import change_basis, rank, structured_ucry
from post196_linear_loader_frames import relative_body
from post218_beam_phase import psynth
from post258_two_stage_anf import decode
from depth_parity_network import walsh
import two_stage_oracle as ts


def parity(v, mask):
    return (v & mask).bit_count() & 1


def descriptor(side, direction, selector):
    cls, rho = (ts.ROWCLS, 32) if side == 'y' else (ts.COLCLS, 48)
    assert parity(direction, selector) and not parity(direction, rho)
    groups = [sorted({(cls[v], cls[v ^ direction]) for v in range(64)
                      if not parity(v, selector) and parity(v, rho) == r})
              for r in (0, 1)]
    assert max(map(len, groups)) <= 8
    keys = []
    for v in range(64):
        v0 = v ^ (direction if parity(v, selector) else 0)
        r = parity(v, rho)
        keys.append((r, groups[r].index((cls[v0], cls[v0 ^ direction]))))
    frame = [rho, selector]
    for mask in sorted(range(1, 64), key=lambda m: (m.bit_count(), m)):
        if not parity(mask, direction) and rank(frame + [mask]) > len(frame):
            frame.append(mask)
    assert len(frame) == 6
    return dict(side=side, direction=direction, selector=selector, rho=rho,
                groups=groups, keys=keys, frame=frame)


def codes(desc, labels):
    return [parity(v, desc['rho']) | (parity(v, desc['selector']) << 1)
            | (labels[r][i] << 2) for v, (r, i) in enumerate(desc['keys'])]


def fixed_codes(side):
    data = json.loads(Path('artifacts/185/class_codes.json').read_text())
    cls, rho = (ts.ROWCLS, 32) if side == 'y' else (ts.COLCLS, 48)
    lab = decode(data[side + 'lab'])
    return [parity(v, rho) | (lab[(parity(v, rho), c)] << 1)
            for v, c in enumerate(cls)]


class Completion:
    def __init__(self, ny, nx):
        self.ny, self.nx = ny, nx
        self.n = ny + nx
        self.order = sorted(range(1 << self.n), key=lambda m: (m.bit_count(), m))
        self.evals = [sum(1 << i for i, m in enumerate(self.order) if m & ~w == 0)
                      for w in range(1 << self.n)]
        self.weights = [0 if m == 0 else 2 ** max(0, m.bit_count() - 2)
                        for m in self.order]

    def solve(self, ycode, xcode):
        care = {}
        for y in range(64):
            for x in range(64):
                word = ycode[y] | (xcode[x] << self.ny)
                bit = int(ts.logo(x, y))
                assert care.setdefault(word, bit) == bit
        piv = {}
        for word, rhs in care.items():
            row = self.evals[word]
            while row:
                i = (row & -row).bit_length() - 1
                if i not in piv:
                    piv[i] = row, rhs
                    break
                a, b = piv[i]
                row ^= a
                rhs ^= b
            else:
                assert rhs == 0
        sol = 0
        for i in sorted(piv, reverse=True):
            row, rhs = piv[i]
            if ((row & sol).bit_count() & 1) ^ rhs:
                sol |= 1 << i
        terms = [m for i, m in enumerate(self.order) if sol >> i & 1]
        score = sum(w for i, w in enumerate(self.weights) if sol >> i & 1)
        return score, terms, care

    def spectrum(self, terms):
        lifted = np.array([sum(m & ~w == 0 for m in terms)
                           for w in range(1 << self.n)], float)
        return walsh(lifted)


def make_loader(desc, labels, seeds=12):
    f = codes(desc, labels)
    frame = desc['frame']
    linear = change_basis(tuple(1 << b for b in range(6)), tuple(frame))
    vals = [0] * 64
    for v in range(64):
        w = sum(parity(v, mask) << b for b, mask in enumerate(frame))
        vals[w] = f[v] >> 2
    # The selector occupies transformed wire 1 and is absent from the label.
    assert all(vals[w] == vals[w ^ 2] for w in range(64))
    table = math.pi * np.array([[v >> b & 1 for v in vals] for b in range(3)])
    best = None
    for seed in range(seeds):
        for sparse, opened in ((True, False), (False, True)):
            raw = structured_ucry(table, [6, 7, 8], list(range(6)), seed,
                                  sparse=sparse, open_walk=opened)
            q = QuantumCircuit(9)
            q.compose(linear, list(range(6)), inplace=True)
            q.compose(relative_body(raw), inplace=True)
            q = native(q)
            score = q.depth(), q.count_ops().get('cx', 0)
            if best is None or score < best[0]:
                best = score, q, dict(seed=seed, sparse=sparse, opened=opened)
    score, q, meta = best
    q = qasm2.loads(qasm2.dumps(q))
    op = Operator(q).data[:, :64]
    indices = [sum(parity(v, mask) << b for b, mask in enumerate(frame))
               | ((f[v] >> 2) << 6) for v in range(64)]
    amplitudes = op[indices, np.arange(64)]
    want = np.zeros_like(op)
    want[indices, np.arange(64)] = amplitudes / np.maximum(abs(amplitudes), 1e-30)
    error = float(np.max(abs(op - want)))
    assert error < 1e-10
    return q, dict(**meta, depth=score[0], cx=score[1], error=error)


def search(outdir, seconds=90, seed=185, variants=('both',)):
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    rng = random.Random(seed)
    # Distinct feasible x pairings, including a direction absent from the note.
    choices = [(16, 16, 4, 12), (16, 16, 55, 16), (16, 16, 59, 16)]
    rows = []
    for variant in variants:
        for yd, ys, xd, xs in choices:
            dy, dx = descriptor('y', yd, ys), descriptor('x', xd, xs)
            ny, nx = (4 if variant == 'x' else 5), (4 if variant == 'y' else 5)
            problem = Completion(ny, nx)
            active = [s for s in ('y', 'x') if variant == 'both' or variant == s]
            labels = {s: [list(range(len(g))) for g in d['groups']]
                      for s, d in [('y', dy), ('x', dx)]}

            def evaluate():
                yc = codes(dy, labels['y']) if ny == 5 else fixed_codes('y')
                xc = codes(dx, labels['x']) if nx == 5 else fixed_codes('x')
                return problem.solve(yc, xc), yc, xc

            (cost, terms, care), yc, xc = evaluate()
            best = cost
            start = time.monotonic()
            steps = 0
            improvements = []
            while True:
                if steps == 0 or cost < best:
                    best = cost
                    co = problem.spectrum(terms)
                    item = dict(variant=variant, y=dy, x=dx, labels=json.loads(json.dumps(labels)),
                                cost=cost, terms=terms, support=int(np.count_nonzero(abs(co[1:]) > 1e-10)),
                                ycode=yc, xcode=xc, ny=ny, nx=nx, step=steps)
                    improvements.append(item)
                    print('best', variant, xd, steps, cost, len(terms), item['support'], flush=True)
                if time.monotonic() - start >= seconds:
                    break
                side = rng.choice(active)
                r = rng.randrange(2)
                a = rng.randrange(len(labels[side][r]))
                b = rng.randrange(8)
                prev = labels[side][r].copy()
                old = prev[a]
                if b in prev:
                    labels[side][r][prev.index(b)] = old
                labels[side][r][a] = b
                (new, nt, nc), yn, xn = evaluate()
                temperature = 2 + 25 * (1 - (steps % 80) / 80)
                if new <= cost or rng.random() < math.exp(min(0, (cost - new) / temperature)):
                    cost, terms, care, yc, xc = new, nt, nc, yn, xn
                else:
                    labels[side][r] = prev
                steps += 1
            row = dict(variant=variant, x_direction=xd, steps=steps,
                       seconds=time.monotonic() - start, improvements=improvements)
            rows.append(row)
            (outdir / 'search.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


def compile_one(item, outdir, seeds=8, coefficients=None):
    outdir.mkdir(parents=True, exist_ok=False)
    ny, nx = item['ny'], item['nx']
    problem = Completion(ny, nx)
    co = problem.spectrum(item['terms']) if coefficients is None else np.asarray(coefficients, float)
    _, _, care = problem.solve(item['ycode'], item['xcode'])
    enc = QuantumCircuit(18)
    kw = []
    report = dict(source=item, loaders=[], coefficients=co.tolist(),
                  coefficient_source='integer_anf' if coefficients is None else 'care_completion')
    for side, bits, wires in [('y', ny, ts.YW + ts.YA), ('x', nx, ts.XW + ts.XA)]:
        if bits == 5:
            q, meta = make_loader(item[side], item['labels'][side], seeds)
            kw += [wires[b] for b in [0, 1, 6, 7, 8]]
        else:
            from post188_sparse_code_revisit import loader
            q, meta = loader(item[side + 'code'], 32 if side == 'y' else 48, seeds)
            kw += [wires[b] for b in [meta['raw_bit'], 6, 7, 8]]
        enc.compose(q, wires, inplace=True)
        report['loaders'].append(meta)
        (outdir / f'{side}_loader.qasm').write_text(qasm2.dumps(q))
    best = None
    for seed in range(2):
        kernel = native(psynth(problem.n, {m: float(co[m]) * math.pi
                                          for m in range(1, len(co)) if abs(co[m]) > 1e-10},
                               global_phase=float(co[0]) * math.pi, seed=seed,
                               beam=24, branch=10, alpha=6., timew=0.5, max_steps=512))
        op = Operator(kernel).data[:, sorted(care)]
        want = np.zeros_like(op)
        want[sorted(care), np.arange(len(care))] = [(-1) ** care[w] for w in sorted(care)]
        phase = np.vdot(want, op)
        error = float(np.max(abs(op - phase / abs(phase) * want)))
        assert error < 1e-9
        q = native(enc.compose(kernel, kw).compose(enc.inverse()))
        score = q.depth(), q.count_ops().get('cx', 0)
        if best is None or score < best[0]:
            best = score, q, dict(depth=kernel.depth(), cx=kernel.count_ops().get('cx', 0),
                                  error=error, seed=seed)
    score, q, meta = best
    path = outdir / f'oracle_d{score[0]}_cx{score[1]}.qasm'
    path.write_text(qasm2.dumps(q))
    serialized = qasm2.load(path)
    assert serialized.depth() == score[0] and serialized.num_qubits == 18
    assert set(serialized.count_ops()) <= {'u3', 'cx'}
    report.update(kernel=meta, depth=score[0], cx=score[1], path=str(path),
                  sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (outdir / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('compiled', {k: report[k] for k in ['loaders', 'kernel', 'depth', 'cx', 'path']}, flush=True)
    from exhaustive_verify import exhaustive
    exhaustive(path)
    return report


def care_completion(item, seconds=30, seed=185):
    """Bounded reweighted L1 completion, retaining actual phase witnesses.

    Alternates the Boolean and integer-ANF lifts on reachable words. Neither
    support nor the LP objective is a depth bound. Compile the returned phases.
    """
    from scipy.optimize import linprog
    p = Completion(item['ny'], item['nx'])
    _, _, care = p.solve(item['ycode'], item['xcode'])
    words = sorted(care)
    h = np.array([[(-1) ** parity(w, m) for m in range(1 << p.n)] for w in words], float)
    matrix = np.c_[h, -h]
    truth = np.array([care[w] for w in words], float)
    lifted = np.array([sum(m & ~w == 0 for m in item['terms']) for w in words], float)
    best_co = p.spectrum(item['terms'])
    best = int(np.count_nonzero(abs(best_co[1:]) > 1e-9))
    rng = np.random.default_rng(seed)
    weights = np.ones(1 << p.n)
    start = time.monotonic()
    history = []
    iteration = 0
    while time.monotonic() - start < seconds:
        restart = iteration // 4
        if iteration % 4 == 0:
            weights = np.exp(rng.normal(0, .7, len(weights)))
        weights[0] = 0
        target = truth if restart % 2 == 0 else lifted
        remain = max(.01, seconds - (time.monotonic() - start))
        result = linprog(np.r_[weights, weights], A_eq=matrix, b_eq=target,
                         bounds=(0, None), method='highs', options={'time_limit': remain})
        if not result.success:
            history.append(dict(iteration=iteration, status=result.message))
            break
        co = result.x[:len(weights)] - result.x[len(weights):]
        co[abs(co) < 1e-9] = 0
        error = float(np.max(abs(h @ co - target)))
        assert error < 1e-8
        size = int(np.count_nonzero(co[1:]))
        history.append(dict(iteration=iteration, support=size, residual=error,
                            lift='truth' if restart % 2 == 0 else 'integer_anf'))
        if size < best:
            best, best_co = size, co.copy()
        weights = np.exp(rng.normal(0, .15, len(weights))) / (abs(co) + .03)
        iteration += 1
    return dict(source=item, support=best, co=best_co.tolist(), history=history,
                seed=seed, seconds=time.monotonic() - start)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=30)
    p.add_argument('--variants', nargs='+', choices=['both', 'x', 'y'], default=['both'])
    p.add_argument('--compile', action='store_true')
    a = p.parse_args()
    rows = search(a.outdir, a.seconds, variants=a.variants)
    if a.compile:
        for i, row in enumerate(rows):
            item = min(row['improvements'], key=lambda r: (r['support'], r['cost']))
            compile_one(item, a.outdir / f'compiled{i}')
