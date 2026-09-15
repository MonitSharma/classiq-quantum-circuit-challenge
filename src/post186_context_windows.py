"""Context-scored four/five-wire phase-network rewrites of the whole oracle."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

from qiskit import qasm2
from qiskit.quantum_info import Operator
from distributed_frame_search import native
from post186_exact_local_phase import collect, extract, replace
from post190_commuting_schedule import records
from post190_window_phase import polynomial, finish_to, sliceq
from post218_beam_phase import psynth
from post258_joint_encoder_schedule import touches


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    q = qasm2.load(a.source)
    best = (q.depth(), q.count_ops().get('cx', 0), len(q.data))
    start = time.monotonic()
    rng = random.Random(a.seed)
    rows, history, failures = [], [], []
    seen = set()
    attempts = 0
    while len(rows) < a.trials and time.monotonic()-start < a.seconds:
        ops = records(q)
        anchor = rng.choice([i for i, op in enumerate(ops) if op[0] == 'cx'])
        wires = set(ops[anchor][1])
        nearby = [op[1] for op in ops[anchor:anchor+130] if op[0] == 'cx']
        while len(wires) < a.width:
            possible = sorted({w for ws in nearby if set(ws) & wires for w in ws} - wires)
            if not possible:
                break
            wires.add(rng.choice(possible))
        attempts += 1
        if len(wires) != a.width:
            continue
        wires = tuple(sorted(wires))
        selected = collect(ops, anchor, wires, limit=260)
        if len(selected) < 7 or len(selected) > 60:
            continue
        key = tuple(ops[i] for i in selected)
        if key in seen:
            continue
        seen.add(key)
        old = extract(q, selected, wires)
        targets, goal, phase = polynomial(old)
        prefix_times = touches(sliceq(q, 0, selected[0]))
        # All selected gates can move before these unselected suffix gates.
        suffix = q.copy_empty_like()
        selected_set = set(selected)
        for i in range(selected[0], len(q.data)):
            if i not in selected_set:
                inst = q.data[i]
                suffix.append(inst.operation, [q.find_bit(w).index for w in inst.qubits])
        tail_times = touches(suffix.reverse_ops())
        arrival = [prefix_times[w] for w in wires]
        departure = [tail_times[w] for w in wires]
        def finalize(body, basis):
            result = finish_to(body, basis, goal)
            times = touches(result, arrival)
            return (max(t+d for t, d in zip(times, departure)), len(result.data)), result
        try:
            replacement = native(psynth(a.width, targets, global_phase=phase, seed=len(rows),
                                       beam=32, branch=8, alpha=6, timew=1.2, horizon=0,
                                       fill=2, initial_times=arrival, finalize=finalize,
                                       max_steps=128))
        except AssertionError as error:
            if str(error) != 'phase schedule did not converge':
                raise
            failures.append(dict(attempt=attempts, wires=wires, selected=selected,
                                 status='Search step limit; no conclusion'))
            continue
        assert Operator(old).equiv(Operator(replacement), atol=1e-9, rtol=0)
        full = native(replace(q, selected, replacement, wires))
        score = (full.depth(), full.count_ops().get('cx', 0), len(full.data))
        row = dict(attempt=attempts, wires=wires, selected=selected, local_before=[old.depth(), len(old.data)],
                   local_after=[replacement.depth(), len(replacement.data)], depth=score[0], cx=score[1])
        rows.append(row)
        if score < best:
            q = full
            best = score
            path = a.outdir/f'candidate{len(history)}_d{score[0]}_cx{score[1]}.qasm'
            path.write_text(qasm2.dumps(q))
            from exhaustive_verify import exhaustive
            exhaustive(path)
            history.append(dict(**row, path=str(path), replacement=qasm2.dumps(replacement)))
            print('IMPROVED', best, 'window', len(rows), flush=True)
            seen.clear()
        if len(rows) % 20 == 0:
            print('window', len(rows), 'best', best, 'last', score, flush=True)
            (a.outdir/'checkpoint.json').write_text(json.dumps(dict(rows=rows, history=history,
                                                                  failures=failures), indent=2)+'\n')
    report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                  width=a.width, attempts=attempts, windows=len(rows), best=best,
                  seconds=time.monotonic()-start, history=history, rows=rows, failures=failures)
    (a.outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print({k: v for k, v in report.items() if k not in ('history', 'rows')}, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/186/two_stage_186.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--width', type=int, choices=[4, 5], default=4)
    p.add_argument('--trials', type=int, default=160)
    p.add_argument('--seconds', type=float, default=100)
    p.add_argument('--seed', type=int, default=186)
    run(p.parse_args())
