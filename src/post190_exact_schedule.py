"""Bounded CP-SAT scheduling of the protected native circuit's commuting gates.

Optional OR-Tools dependency may live outside the workspace (set PYTHONPATH).
The lower bound and any optimality result concern this fixed commutation DAG.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

from ortools.sat.python import cp_model
from qiskit import qasm2
from post190_commuting_schedule import dependency_graph, reordered


def run(source, outdir, seconds, hint_path=None):
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    text = source.read_text()
    q = qasm2.loads(text)
    ops, succ, pred = dependency_graph(q)
    n = len(ops)
    earliest, height = [0] * n, [1] * n
    for i in range(n):
        earliest[i] = max((earliest[j] + 1 for j in pred[i]), default=0)
    for i in reversed(range(n)):
        height[i] = 1 + max((height[j] for j in succ[i]), default=0)
    order = list(range(n))
    if hint_path:
        order = json.loads(hint_path.read_text())['history'][-1]['order']
    clocks, hints = [0] * q.num_qubits, [0] * n
    for i in order:
        hints[i] = max(clocks[w] for w in ops[i][1])
        for w in ops[i][1]:
            clocks[w] = hints[i] + 1
    upper = max(clocks)
    lower = max(max(height), max(sum(w in op[1] for op in ops) for w in range(q.num_qubits)))
    model = cp_model.CpModel()
    starts = [model.new_int_var(earliest[i], upper-height[i], f't{i}') for i in range(n)]
    span = model.new_int_var(lower, upper, 'depth')
    for i in range(n):
        model.add(starts[i] + height[i] <= span)
        for j in succ[i]:
            model.add(starts[j] >= starts[i] + 1)
        model.add_hint(starts[i], hints[i])
    for w in range(q.num_qubits):
        # Unit-duration intervals cannot share a wire in a native layer.
        model.add_all_different([starts[i] for i in range(n) if w in ops[i][1]])
    model.add_hint(span, upper)
    model.minimize(span)
    model_error = model.validate()
    assert not model_error, model_error
    history = []

    class Save(cp_model.CpSolverSolutionCallback):
        def on_solution_callback(self):
            depth = self.value(span)
            if history and depth >= history[-1]['depth']:
                return
            layers = [[] for _ in range(depth)]
            for i, t in enumerate(starts):
                layers[self.value(t)].append(i)
            candidate = reordered(q, layers, pred)
            source_out = qasm2.dumps(candidate)
            actual = qasm2.loads(source_out)
            assert actual.depth() <= depth
            path = outdir / f'oracle_d{actual.depth()}_cx{actual.count_ops().get("cx", 0)}.qasm'
            if not path.exists():
                path.write_text(source_out)
            row = dict(depth=actual.depth(), objective=depth, path=str(path),
                       seconds=self.wall_time, order=[i for layer in layers for i in layer])
            history.append(row)
            (outdir/'checkpoint.json').write_text(json.dumps(dict(history=history), indent=2)+'\n')
            print('solution', actual.depth(), 'bound', self.best_objective_bound, flush=True)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 190
    solver.parameters.log_search_progress = False
    started = time.monotonic()
    status = solver.solve(model, Save())
    report = dict(source=str(source), source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                  status=solver.status_name(status), initial_depth=upper, analytic_lower_bound=lower,
                  solver_lower_bound=solver.best_objective_bound, seconds=time.monotonic()-started,
                  history=history, scope='Fixed native gates and conservative commutation DAG only')
    (outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print({k:v for k,v in report.items() if k!='history'}, flush=True)
    if history:
        from exhaustive_verify import exhaustive
        exhaustive(Path(history[-1]['path']))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/190/two_stage_190.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=55)
    p.add_argument('--hint', type=Path)
    a = p.parse_args()
    run(a.source, a.outdir, a.seconds, a.hint)
