"""Construct and measure nine-wire v2 encoders; never overwrite oracle artifacts.

Enumerate codebooks with two potentially split levels. Fix an output affine
frame during codebook construction, solve degree constraints linearly in one
choice bit per input, then search output linear frames for inexpensive ESOPs.
This is a bounded construction family, not a native-depth lower bound.
All dirty-helper primitives are full monomial operations, never action-only.
"""
import argparse
import functools
import hashlib
import itertools
import json
import random
import time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.circuit.library import RC3XGate
from qiskit.quantum_info import Operator
from qiskit.synthesis.multi_controlled import synth_mcx_n_dirty_i15, synth_mcx_noaux_v24
from level_degree3_codes import level_table, verify_code
from search import esop

LEVELS = level_table('v2')
FULL = (1 << 64) - 1


def affine_solution(rows, n):
    pivots = {}
    mask = (1 << n) - 1
    for row in rows:
        while row & mask:
            i = ((row & mask) & -(row & mask)).bit_length() - 1
            if i in pivots:
                row ^= pivots[i]
            else:
                pivots[i] = row
                break
        else:
            if row >> n:
                return None
    return pivots


def complete(pivots, n, initial):
    solution = initial
    for i in pivots:
        solution &= ~(1 << i)
    for i in sorted(pivots, reverse=True):
        if ((pivots[i] & solution).bit_count() ^ (pivots[i] >> n)) & 1:
            solution ^= 1 << i
    return solution


def code_candidates(degree=5):
    for split in itertools.combinations(range(6), 2):
        singles = [l for l in range(6) if l not in split]
        points = [p for p in range(64) if LEVELS[p] in split]
        for fourth in range(3, 8):
            unused = set(range(8)) - {0, 1, 2, fourth}
            for pair in itertools.combinations(sorted(unused), 2):
                book = {l: (c, c) for l, c in zip(singles, (0, 1, 2, fourth))}
                book[split[0]] = pair
                book[split[1]] = tuple(sorted(unused - set(pair)))
                rows = []
                for bit in range(3):
                    for monomial in range(64):
                        if monomial.bit_count() <= degree:
                            continue
                        rhs = sum(book[LEVELS[p]][0] >> bit & 1 for p in range(64)
                                  if p & monomial == p) & 1
                        row = sum(1 << i for i, p in enumerate(points) if p & monomial == p
                                  and (book[LEVELS[p]][0] ^ book[LEVELS[p]][1]) >> bit & 1)
                        rows.append(row | (rhs << len(points)))
                pivots = affine_solution(rows, len(points))
                if pivots is None:
                    continue
                # Smooth free assignments, not random truth tables.
                for selector in (0, 1, 2, 4, 8, 16, 32, 63):
                    initial = sum(((p & selector).bit_count() & 1) << i for i, p in enumerate(points))
                    solution = complete(pivots, len(points), initial)
                    codes = [book[LEVELS[p]][0] for p in range(64)]
                    for i, p in enumerate(points):
                        codes[p] = book[LEVELS[p]][solution >> i & 1]
                    tables = tuple(sum((codes[p] >> b & 1) << p for p in range(64)) for b in range(3))
                    verify_code('v2', tables)
                    yield tables, dict(split=split, fourth=fourth, pair=pair, selector=selector)


@functools.lru_cache(None)
def primitive(n):
    if n <= 2:
        q = QuantumCircuit(n + 1)
        if n == 0: q.x(0)
        elif n == 1: q.cx(0, 1)
        else: q.rccx(0, 1, 2)
    elif n == 3:
        q = QuantumCircuit(4)
        q.append(RC3XGate(), range(4))
    elif n <= 5:
        q = synth_mcx_n_dirty_i15(n, relative_phase=True, action_only=False)
    else:
        q = synth_mcx_noaux_v24(n)
    return transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                     optimization_level=3, seed_transpiler=0)


def primitive_check(n):
    q = primitive(n)
    op = Operator(q).data
    for x in range(1 << q.num_qubits):
        want = x ^ ((1 << n) if x & ((1 << n) - 1) == (1 << n) - 1 else 0)
        assert abs(abs(op[want, x]) - 1) < 1e-10
    return dict(controls=n, width=q.num_qubits, depth=q.depth(), cx=q.count_ops().get('cx', 0))


@functools.lru_cache(maxsize=12000)
def table_terms(table):
    options = [(esop(table, 6), False), (esop(table ^ FULL, 6), True)]
    return min(options, key=lambda item: sum(primitive(m.bit_count()).depth() + 2 * bool(m ^ v)
                                            for m, v in item[0]) + item[1])


def frames(tables):
    values = [0] * 8
    for m in range(1, 8):
        values[m] = functools.reduce(int.__xor__, (tables[b] for b in range(3) if m >> b & 1), 0)
    costs = {m: sum(primitive(mask.bit_count()).depth() + 2 * bool(mask ^ val)
                   for mask, val in table_terms(values[m])[0]) for m in range(1, 8)}
    # Permuting output wires does not alter this score; count each basis once.
    triples = [t for t in itertools.combinations(range(1, 8), 3) if t[0] ^ t[1] ^ t[2] != 0]
    best = min(triples, key=lambda t: (max(costs[m] for m in t), sum(costs[m] for m in t)))
    return tuple(values[m] for m in best), (max(costs[m] for m in best), sum(costs[m] for m in best))


def build(tables, seed):
    rng = random.Random(seed)
    q = QuantumCircuit(9)
    jobs = []
    for bit, table in enumerate(tables):
        terms, complement = table_terms(table)
        if complement: q.x(6 + bit)
        for mask, val in terms:
            controls = [i for i in range(6) if mask >> i & 1]
            negatives = [i for i in controls if not val >> i & 1]
            local = primitive(len(controls))
            helper_count = local.num_qubits - len(controls) - 1
            spare = [i for i in range(9) if i not in controls and i != 6 + bit]
            rng.shuffle(spare)
            mapping = controls + [6 + bit] + spare[:helper_count]
            block = QuantumCircuit(9)
            for i in negatives: block.x(i)
            block.compose(local, mapping, inplace=True)
            for i in negatives: block.x(i)
            jobs.append(block)
    # Whole monomial toggles commute classically here. Their phases may change
    # with order but cancel in E-dagger K E for diagonal K.
    rng.shuffle(jobs)
    while jobs:
        # Native DAG depth after append is the local scheduling objective.
        scored = [(q.compose(block).depth(), i) for i, block in enumerate(jobs)]
        _, chosen = min(scored)
        q.compose(jobs.pop(chosen), inplace=True)
    return transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                     optimization_level=3, seed_transpiler=seed)


def verify_saved(path, tables):
    source = Path(path).read_text()
    q = qasm2.loads(source)
    assert q.num_qubits == 9 and set(q.count_ops()) <= {'u3', 'cx'}
    op = Operator(q).data
    codes = verify_code('v2', tables)
    max_error = 0.0
    for original in range(64):
        expected = original | (codes[original] << 6)
        column = op[:, original].copy()
        amp = column[expected]
        max_error = max(max_error, abs(abs(amp) - 1))
        column[expected] = 0
        max_error = max(max_error, float(np.max(np.abs(column))))
    assert max_error < 1e-10
    # Verify every code-parity diagonal sandwiched by the exact inverse.
    sandwich_error = 0.0
    for mask in range(1, 8):
        diagonal = np.array([(-1)**(((j >> 6) & mask).bit_count() & 1) for j in range(512)])
        got = op.conj().T @ (diagonal[:, None] * op[:, :64])
        expected = np.zeros((512, 64), complex)
        for original in range(64): expected[original, original] = (-1)**((codes[original] & mask).bit_count() & 1)
        sandwich_error = max(sandwich_error, float(np.max(np.abs(got - expected))))
    assert sandwich_error < 1e-10
    return dict(qasm=str(Path(path).resolve()), sha256=hashlib.sha256(source.encode()).hexdigest(),
                width=9, depth=q.depth(), cx=q.count_ops().get('cx', 0), inputs_checked=64,
                max_column_error=max_error, max_phase_sandwich_error=sandwich_error,
                level_codes={str(l): sorted({codes[p] for p in range(64) if LEVELS[p] == l}) for l in range(6)},
                scope='Encoder with input-dependent phases; all six data bits preserved. Not a complete oracle.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=45)
    parser.add_argument('--outdir', default='artifacts/v2_native_checkpoint')
    parser.add_argument('--replay', help='Rebuild the exact best encoder from a saved report')
    args = parser.parse_args()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    if args.replay:
        saved = json.loads(Path(args.replay).read_text())
        path = out / 'encoder.qasm'
        if path.exists(): raise FileExistsError(path)
        tables = saved['truth_tables']
        q = build(tables, saved['seed'])
        path.write_text(qasm2.dumps(q))
        verification = verify_saved(path, tables)
        (out / 'encoder.verification.json').write_text(json.dumps(verification, indent=2) + '\n')
        print(json.dumps(verification, indent=2), flush=True)
        return
    checks = [primitive_check(n) for n in range(7)]
    print('primitive checks', checks, flush=True)
    began = time.monotonic()
    keep = {}
    tried = 0
    for tables, provenance in code_candidates():
        framed, score = frames(tables)
        keep.setdefault(framed, (score, provenance))
        tried += 1
        if tried % 50 == 0: print('codes', tried, 'best proxy', min(v[0] for v in keep.values()), flush=True)
        if time.monotonic() - began > args.seconds: break
    ranked = sorted(keep.items(), key=lambda kv: kv[1][0])[:6]
    best = None
    native = []
    for tables, (proxy, provenance) in ranked:
        for seed in range(3):
            q = build(tables, seed)
            metric = (q.depth(), q.count_ops().get('cx', 0))
            native.append(dict(depth=metric[0], cx=metric[1], tables=tables, seed=seed, proxy=proxy))
            print('native', metric, flush=True)
            if best is None or metric < best[0]: best = (metric, q, tables, provenance, seed)
    metric, q, tables, provenance, seed = best
    path = out / 'encoder.qasm'
    if path.exists(): raise FileExistsError(path)
    path.write_text(qasm2.dumps(q))
    verification = verify_saved(path, tables)
    (out / 'encoder.verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    report = dict(code_candidates=tried, native_candidates=native, primitive_checks=checks,
                  best=verification, truth_tables=tables, provenance=provenance, seed=seed,
                  meets_31_depth_checkpoint=metric[0] <= 31, seconds=time.monotonic() - began)
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(verification, indent=2), flush=True)


if __name__ == '__main__': main()
