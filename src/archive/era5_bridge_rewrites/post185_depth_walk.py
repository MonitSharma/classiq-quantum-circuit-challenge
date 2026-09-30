"""Depth-first stochastic CNOT rewriting with neutral/uphill moves.

CX count is only a broad resource cap, never an optimization tie-breaker.
Candidates are ranked by depth and the number of gates on critical paths.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import time

from qiskit import qasm2
from distributed_frame_search import native
from post186_cnot_bridge import rewrite
from post190_commuting_schedule import records, commute, dependency_graph, schedule, reordered


def profile(q):
    ops = records(q)
    clocks = [0] * q.num_qubits
    starts = []
    for _, ws, _ in ops:
        t = max(clocks[w] for w in ws)
        starts.append(t)
        for w in ws:
            clocks[w] = t+1
    depth = max(clocks)
    tails = [0] * q.num_qubits
    critical = set()
    for i in reversed(range(len(ops))):
        ws = ops[i][1]
        t = max(tails[w] for w in ws)+1
        if starts[i]+t == depth:
            critical.add(i)
        for w in ws:
            tails[w] = t
    return depth, critical


def moves_for(q, critical):
    ops = records(q)
    moves, weights = [], []
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
                    weights.append(1 + 5*(i in critical) + 5*(j in critical))
                break
    return moves, weights


def apply_move(q, move, shuffle_seed):
    candidate = native(rewrite(q, *move))
    if shuffle_seed is not None:
        ops, succ, pred = dependency_graph(candidate)
        shuffled = native(reordered(candidate, schedule(ops, succ, pred, shuffle_seed), pred))
        # Equal-depth gate orderings remain useful for the next rewrite.
        if shuffled.depth() <= candidate.depth():
            candidate = shuffled
    return candidate


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    base = qasm2.load(a.source)
    q = base
    best_depth = base.depth()
    depth, critical = profile(q)
    rng = random.Random(a.seed)
    trace = []
    history, pool, seen = [], [], set()
    attempts = accepted = restarts = 0
    started = time.monotonic()
    moves, weights = moves_for(q, critical)
    while attempts < a.trials and time.monotonic()-started < a.seconds:
        attempts += 1
        move = rng.choices(moves, weights)[0]
        shuffle_seed = rng.randrange(24) if rng.random() < .4 else None
        candidate = apply_move(q, move, shuffle_seed)
        d, crit = profile(candidate)
        cx = candidate.count_ops().get('cx', 0)
        # Permit temporary depth increases; no preference for fewer CNOTs.
        allow = d <= best_depth + 3 and cx <= base.count_ops().get('cx', 0)+a.cx_slack
        delta = (d-depth) + .002*(len(crit)-len(critical))
        if allow and (delta <= 0 or rng.random() < math.exp(-delta/.65)):
            q = candidate
            depth, critical = d, crit
            accepted += 1
            trace.append(dict(move=move, shuffle_seed=shuffle_seed))
            moves, weights = moves_for(q, critical)
            if d <= best_depth:
                text = qasm2.dumps(q)
                sha = hashlib.sha256(text.encode()).hexdigest()
                if sha not in seen:
                    seen.add(sha)
                    pool.append(((d, len(crit)), attempts, text, trace.copy()))
                    pool.sort(key=lambda item: (item[0], item[1]))
                    pool = pool[:a.keep]
            if d < best_depth:
                best_depth = d
                path = a.outdir/f'candidate{attempts}_d{d}_cx{cx}.qasm'
                path.write_text(qasm2.dumps(q))
                from exhaustive_verify import exhaustive
                exhaustive(path)
                history.append(dict(attempt=attempts, depth=d, cx=cx, path=str(path), trace=trace.copy()))
                print('DEPTH IMPROVEMENT', d, cx, 'attempt', attempts, flush=True)
        if attempts % 80 == 0:
            print('progress', attempts, 'accepted', accepted, 'best depth', best_depth,
                  'current', depth, 'CX', q.count_ops().get('cx', 0), flush=True)
        if len(trace) >= 24 or attempts % 140 == 0:
            # Diverse restarts prevent one increasing-CX branch consuming the run.
            q = base
            depth, critical = profile(q)
            moves, weights = moves_for(q, critical)
            trace = []
            restarts += 1
    retained = []
    for (d, count), attempt, text, branch in pool:
        path = a.outdir/f'portfolio{attempt}_d{d}.qasm'
        path.write_text(text)
        retained.append(dict(depth=d, critical_gates=count, path=str(path), trace=branch))
    report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                  objective='Depth, then critical-path gate count; CX only constrained by resource cap',
                  cx_slack=a.cx_slack, attempts=attempts, accepted=accepted, restarts=restarts,
                  best_depth=best_depth, seconds=time.monotonic()-started, history=history, retained=retained)
    (a.outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print({k:v for k,v in report.items() if k not in ('history','retained')}, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/185/two_stage_185.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=120)
    p.add_argument('--trials', type=int, default=1400)
    p.add_argument('--seed', type=int, default=185)
    p.add_argument('--cx-slack', type=int, default=80)
    p.add_argument('--keep', type=int, default=8)
    run(p.parse_args())
