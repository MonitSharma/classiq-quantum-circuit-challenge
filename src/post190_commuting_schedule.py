"""Reschedule the exact native gates using conservative commutation relations.

Every original noncommuting pair retains its order. No gate, angle, layout, or
relative phase is changed. This is a fixed-gate optimization, not a global bound.
"""
import argparse
import hashlib
import json
import random
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import U3Gate


def records(q):
    return [(i.operation.name, tuple(q.find_bit(w).index for w in i.qubits),
             tuple(map(float, i.operation.params))) for i in q.data]


@lru_cache(None)
def matrix(params):
    return U3Gate(*params).to_matrix()


@lru_cache(None)
def commute(a, b):
    na, wa, pa = a
    nb, wb, pb = b
    if not set(wa).intersection(wb):
        return True
    if na == nb == 'cx':
        return wa[0] != wb[1] and wb[0] != wa[1]
    if na == nb == 'u3':
        x, y = matrix(pa), matrix(pb)
        return bool(np.max(abs(x @ y - y @ x)) < 1e-12)
    if na == 'u3':
        return commute(b, a)
    assert na == 'cx' and nb == 'u3'
    u = matrix(pb)
    if wb[0] == wa[0]:
        return bool(abs(u[0, 1]) + abs(u[1, 0]) < 1e-12)
    x = np.array([[0, 1], [1, 0]])
    return bool(np.max(abs(u @ x - x @ u)) < 1e-12)


def dependency_graph(q):
    ops = records(q)
    successors = [set() for _ in ops]
    predecessors = [set() for _ in ops]
    seen = [[] for _ in range(q.num_qubits)]
    for j, op in enumerate(ops):
        for i in set(i for w in op[1] for i in seen[w]):
            if not commute(ops[i], op):
                successors[i].add(j)
                predecessors[j].add(i)
        for w in op[1]:
            seen[w].append(j)
    # Remove transitive edges exactly using bitset reachability.
    reach = [0] * len(ops)
    reduced = [[] for _ in ops]
    for i in reversed(range(len(ops))):
        for j in sorted(successors[i]):
            if not (reach[i] >> j & 1):
                reduced[i].append(j)
                reach[i] |= (1 << j) | reach[j]
    pred = [[] for _ in ops]
    for i, nxt in enumerate(reduced):
        for j in nxt:
            pred[j].append(i)
    return ops, reduced, pred


def schedule(ops, succ, pred, seed):
    rng = random.Random(seed)
    n = len(ops)
    height = [1] * n
    tails = np.zeros((n, max(w for _, ws, _ in ops for w in ws) + 1), int)
    for i in reversed(range(n)):
        if succ[i]:
            height[i] += max(height[j] for j in succ[i])
            tails[i] = tails[succ[i]].max(axis=0)
        tails[i, list(ops[i][1])] += 1
    counts = list(map(len, pred))
    ready = {i for i in range(n) if counts[i] == 0}
    layers = []
    noise = [0, .3, 1, 2, 4, 8][seed % 6]
    weight = [0, .2, .5, 1][(seed // 6) % 4]
    while ready:
        ranked = sorted(ready, key=lambda i: (height[i] + weight * tails[i].max()
                                               + noise * rng.random(), -i), reverse=True)
        used, layer = set(), []
        for i in ranked:
            if used.isdisjoint(ops[i][1]):
                layer.append(i)
                used.update(ops[i][1])
        ready.difference_update(layer)
        for i in layer:
            for j in succ[i]:
                counts[j] -= 1
                if counts[j] == 0:
                    ready.add(j)
        layers.append(layer)
    assert sum(map(len, layers)) == n
    return layers


def reordered(q, layers, pred):
    order = [i for layer in layers for i in layer]
    positions = {i: p for p, i in enumerate(order)}
    assert len(positions) == len(q.data)
    assert all(positions[i] < positions[j] for j, ps in enumerate(pred) for i in ps)
    out = QuantumCircuit(q.num_qubits, global_phase=q.global_phase)
    for i in order:
        inst = q.data[i]
        out.append(inst.operation, [q.find_bit(w).index for w in inst.qubits])
    return out


def run(source, outdir, seconds, trials):
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    original = source.read_text()
    q = qasm2.loads(original)
    started = time.monotonic()
    ops, succ, pred = dependency_graph(q)
    print('graph', len(ops), sum(map(len, succ)), flush=True)
    best = q.depth()
    history = []
    completed = 0
    for seed in range(trials):
        if completed and time.monotonic() - started >= seconds:
            break
        layers = schedule(ops, succ, pred, seed)
        completed += 1
        if len(layers) < best:
            candidate = reordered(q, layers, pred)
            assert candidate.depth() <= len(layers)
            best = candidate.depth()
            path = outdir / f'oracle_d{best}_cx{candidate.count_ops().get("cx", 0)}.qasm'
            path.write_text(qasm2.dumps(candidate))
            row = dict(seed=seed, depth=best, path=str(path), order=[i for l in layers for i in l])
            history.append(row)
            print('improved', seed, best, flush=True)
    report = dict(source=str(source), source_sha256=hashlib.sha256(original.encode()).hexdigest(),
                  initial_depth=q.depth(), best_depth=best, trials_completed=completed,
                  seconds=time.monotonic()-started, history=history)
    (outdir / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print({k: v for k, v in report.items() if k != 'history'}, flush=True)
    if history:
        from exhaustive_verify import exhaustive
        exhaustive(Path(history[-1]['path']))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/190/two_stage_190.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=60)
    p.add_argument('--trials', type=int, default=2000)
    a = p.parse_args()
    run(a.source, a.outdir, a.seconds, a.trials)
