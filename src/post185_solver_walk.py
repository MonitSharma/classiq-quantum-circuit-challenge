"""Explore multi-rewrite branches with a solver-enforced depth ceiling.

No CX-count objective. Equal-depth branches are kept for different critical
paths, and the solver runs before rejecting a rewritten gate network.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

from ortools.sat.python import cp_model
from qiskit import qasm2
from post185_depth_walk import apply_move, profile, moves_for
from post190_commuting_schedule import dependency_graph, reordered


def bounded_schedule(q, ceiling, seconds, seed):
    ops, succ, pred = dependency_graph(q)
    n = len(ops)
    earliest, height = [0]*n, [1]*n
    for i in range(n):
        earliest[i] = max((earliest[j]+1 for j in pred[i]), default=0)
    for i in reversed(range(n)):
        height[i] = 1+max((height[j] for j in succ[i]), default=0)
    lower = max(max(height), max(sum(w in op[1] for op in ops) for w in range(q.num_qubits)))
    if lower > ceiling:
        return None, dict(status='Analytic bound exceeds ceiling', lower=lower)
    model = cp_model.CpModel()
    starts = [model.new_int_var(earliest[i], ceiling-height[i], f't{i}') for i in range(n)]
    span = model.new_int_var(lower, ceiling, 'depth')
    for i in range(n):
        model.add(starts[i]+height[i] <= span)
        for j in succ[i]:
            model.add(starts[j] >= starts[i]+1)
    for w in range(q.num_qubits):
        model.add_all_different([starts[i] for i in range(n) if w in ops[i][1]])
    model.minimize(span)
    if q.depth() <= ceiling:
        clocks = [0]*q.num_qubits
        for i, (_, ws, _) in enumerate(ops):
            t = max(clocks[w] for w in ws)
            model.add_hint(starts[i], t)
            for w in ws:
                clocks[w] = t+1
        model.add_hint(span, max(clocks))
    assert not model.validate(), model.validate()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = seed
    status = solver.solve(model)
    report = dict(status=solver.status_name(status), lower=solver.best_objective_bound,
                  ceiling=ceiling, seconds=solver.wall_time)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, report
    layers = [[] for _ in range(solver.value(span))]
    for i, t in enumerate(starts):
        layers[solver.value(t)].append(i)
    report['order'] = [i for layer in layers for i in layer]
    result = reordered(q, layers, pred)
    report['depth'] = result.depth()
    return result, report


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    base = qasm2.load(a.source)
    pool = [(base, str(a.source))]
    best = base.depth()
    rng = random.Random(a.seed)
    rows, history = [], []
    started = time.monotonic()
    seen = set()
    for trial in range(a.trials):
        if time.monotonic()-started > a.seconds:
            break
        parent, parent_path = rng.choice(pool)
        candidate = parent
        trace = []
        for _ in range(rng.choice([1, 1, 2, 2, 3])):
            _, crit = profile(candidate)
            moves, weights = moves_for(candidate, crit)
            move = rng.choices(moves, weights)[0]
            candidate = apply_move(candidate, move, None)
            trace.append(move)
        text = qasm2.dumps(candidate)
        sha = hashlib.sha256(text.encode()).hexdigest()
        if sha in seen:
            continue
        seen.add(sha)
        # Every third solve strictly targets a new depth record; the others
        # preserve equal-depth variants for later combinations.
        ceiling = best-1 if trial % 3 == 0 else best
        scheduled, result = bounded_schedule(candidate, ceiling, a.solve_seconds, a.seed+trial)
        row = dict(trial=trial, parent=parent_path, moves=trace, input_depth=candidate.depth(),
                   input_cx=candidate.count_ops().get('cx',0), source_sha256=sha, solver=result)
        if scheduled is not None:
            source = a.outdir/f'input{trial}.qasm'
            source.write_text(text)
            d, crit = profile(scheduled)
            path = a.outdir/f'candidate{trial}_d{d}_cx{scheduled.count_ops().get("cx",0)}.qasm'
            path.write_text(qasm2.dumps(scheduled))
            row.update(path=str(path), input_path=str(source), depth=d, critical=len(crit))
            pool.append((scheduled, str(path)))
            if len(pool) > 8:
                # Retain the depth champion and stochastic diversity, not CX minima.
                pool.pop(rng.randrange(1, len(pool)-1))
            if d < best:
                from exhaustive_verify import exhaustive
                exhaustive(path)
                best = d
                pool = [(c,p) for c,p in pool if c.depth() <= best]
                history.append(dict(path=str(path), depth=d, trial=trial))
                print('DEPTH IMPROVEMENT', d, 'CX', scheduled.count_ops().get('cx',0), flush=True)
        rows.append(row)
        print('solve', trial, result['status'], result.get('depth'), 'best depth', best, 'parents', len(pool), flush=True)
        report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                      objective='Depth only; preserve neutral branches, no CX cap or penalty',
                      best_depth=best, seconds=time.monotonic()-started, rows=rows, history=history)
        (a.outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/185/two_stage_185.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--trials', type=int, default=50)
    p.add_argument('--seconds', type=float, default=220)
    p.add_argument('--solve-seconds', type=float, default=5)
    p.add_argument('--seed', type=int, default=1852)
    run(p.parse_args())
