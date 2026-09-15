"""Change CNOT connectivity with exact three-wire conjugation identities.

For a three-wire CNOT chain G,H, G H = H K G, where K joins the
chain endpoints. The extra CNOT may relieve a critical scheduling dependency.
Unlike a commuting-gate schedule this changes the circuit's gate multiset.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from qiskit import QuantumCircuit, qasm2
from distributed_frame_search import native
from post190_commuting_schedule import records, commute, dependency_graph, schedule, reordered


def bridge(first, second):
    a, b = first
    c, d = second
    assert len({a, b, c, d}) == 3
    if b == c:
        return a, d
    assert d == a
    return c, b


def rewrite(q, i, j, direction):
    ops = records(q)
    first, second = ops[i], ops[j]
    assert first[0] == second[0] == 'cx' and not commute(first, second)
    assert all(commute(first if direction == 'right' else second, ops[k]) for k in range(i+1, j))
    middle = bridge(first[1], second[1])
    result = QuantumCircuit(q.num_qubits, global_phase=q.global_phase)
    for k, inst in enumerate(q.data):
        if k == (j if direction == 'right' else i):
            result.cx(*second[1])
            result.cx(*middle)
            result.cx(*first[1])
        if k not in (i, j):
            result.append(inst.operation, [q.find_bit(w).index for w in inst.qubits])
    return result


def optimized_move(q, i, j, direction, schedules):
    candidate = native(rewrite(q, i, j, direction))
    ops, succ, pred = dependency_graph(candidate)
    best = candidate
    best_seed = None
    for seed in range(schedules):
        attempt = native(reordered(candidate, schedule(ops, succ, pred, seed), pred))
        if (attempt.depth(), attempt.count_ops().get('cx', 0), len(attempt.data)) < (best.depth(), best.count_ops().get('cx', 0), len(best.data)):
            best = attempt
            best_seed = seed
    return best, best_seed


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    q = qasm2.load(a.source)
    ops = records(q)
    moves = []
    for i, op in enumerate(ops):
        if op[0] != 'cx':
            continue
        for direction, indices in [('right', range(i+1, len(ops))), ('left', range(i-1, -1, -1))]:
            for j in indices:
                other = ops[j]
                if commute(op, other):
                    continue
                if other[0] == 'cx' and len(set(op[1]+other[1])) == 3:
                    moves.append((min(i, j), max(i, j), direction))
                break
    rows, pool, seen = [], [], set()
    started = time.monotonic()
    for index, (i, j, direction) in enumerate(moves):
        best, best_seed = optimized_move(q, i, j, direction, a.schedules)
        text = qasm2.dumps(best)
        digest = hashlib.sha256(text.encode()).hexdigest()
        score = (best.depth(), best.count_ops().get('cx', 0), len(best.data))
        row = dict(index=index, pair=[i, j], direction=direction, best_seed=best_seed,
                   depth=score[0], cx=score[1], gates=score[2], sha256=digest)
        rows.append(row)
        if digest not in seen:
            seen.add(digest)
            pool.append((score, index, text))
            pool.sort()
            pool = pool[:a.keep]
        if index % 25 == 0:
            print('move', index, 'of', len(moves), 'best', pool[0][0], flush=True)
    for score, index, text in pool:
        path = a.outdir/f'candidate{index}_d{score[0]}_cx{score[1]}.qasm'
        path.write_text(text)
        rows[index]['path'] = str(path)
    report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                  moves=len(moves), schedules_per_move=a.schedules, seconds=time.monotonic()-started,
                  retained=[r for r in rows if 'path' in r], rows=rows,
                  verification='Local identity checked in tests; retained full candidates require exhaustive acceptance')
    (a.outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('retained', [(score, index) for score, index, _ in pool], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/186/two_stage_186.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--schedules', type=int, default=3)
    p.add_argument('--keep', type=int, default=10)
    run(p.parse_args())
