"""Depth search using dirty-wire mediation of individual critical CNOTs.

CX(a,k), CX(k,b), CX(a,k), CX(k,b) equals CX(a,b) for arbitrary k.
The helper is restored without assuming a clean state. More gates can expose
different cancellation/commutation opportunities in surrounding circuitry.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

from qiskit import QuantumCircuit, qasm2
from distributed_frame_search import native
from post185_depth_walk import profile
from post190_commuting_schedule import records, dependency_graph, schedule, reordered


def mediated(q, index, helper, reverse):
    inst = q.data[index]
    assert inst.operation.name == 'cx'
    a, b = [q.find_bit(w).index for w in inst.qubits]
    assert helper not in (a, b)
    pairs = [(a, helper), (helper, b), (a, helper), (helper, b)]
    if reverse:
        pairs.reverse()
    result = QuantumCircuit(q.num_qubits, global_phase=q.global_phase)
    for i, inst in enumerate(q.data):
        if i == index:
            for pair in pairs:
                result.cx(*pair)
        else:
            result.append(inst.operation, [q.find_bit(w).index for w in inst.qubits])
    return result


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    q = qasm2.load(a.source)
    ops = records(q)
    _, critical = profile(q)
    rng = random.Random(a.seed)
    moves = []
    for i in sorted(critical):
        if ops[i][0] != 'cx':
            continue
        nearby = {w for op in ops[max(0, i-25):i+26] for w in op[1]} - set(ops[i][1])
        for helper in sorted(nearby):
            for reverse in (False, True):
                moves.append((i, helper, reverse))
    rng.shuffle(moves)
    rows, pool, seen = [], [], set()
    start = time.monotonic()
    for i, move in enumerate(moves[:a.trials]):
        if time.monotonic()-start >= a.seconds:
            break
        candidate = native(mediated(q, *move))
        graph, succ, pred = dependency_graph(candidate)
        # Try a second order, but depth is always the primary score.
        for seed in (0, 1):
            attempt = native(reordered(candidate, schedule(graph, succ, pred, seed), pred))
            if attempt.depth() < candidate.depth():
                candidate = attempt
                break
        d, crit = profile(candidate)
        score = (d, len(crit))
        text = qasm2.dumps(candidate)
        sha = hashlib.sha256(text.encode()).hexdigest()
        row = dict(trial=i, move=move, depth=d, critical=len(crit), cx=candidate.count_ops().get('cx',0), sha256=sha)
        rows.append(row)
        if sha not in seen:
            seen.add(sha)
            pool.append((score, i, text))
            pool.sort()
            pool = pool[:a.keep]
        if i % 50 == 0:
            print('trial', i, 'best depth/critical', pool[0][0], flush=True)
    for score, i, text in pool:
        path = a.outdir/f'candidate{i}_d{score[0]}.qasm'
        path.write_text(text)
        rows[i]['path'] = str(path)
    report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                  possible_moves=len(moves), trials=len(rows), seconds=time.monotonic()-start,
                  objective='Depth, then critical-gate count; no CX tie-breaker',
                  retained=[r for r in rows if 'path' in r], rows=rows)
    (a.outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('retained', [(s, i) for s, i, _ in pool], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/185/two_stage_185.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--trials', type=int, default=600)
    p.add_argument('--seconds', type=float, default=100)
    p.add_argument('--seed', type=int, default=1851)
    p.add_argument('--keep', type=int, default=8)
    run(p.parse_args())
