"""Total-depth SAT parity resynthesis on larger convex CNOT/phase blocks.

Inspired by HOPPS (arXiv:2511.18770), with explicit one-qubit phase slots and
optional per-wire release/deadline constraints. Not an upstream implementation.
Arbitrary input values are preserved; no clean-workspace assumption is made.
"""
import argparse
import hashlib
import itertools
import json
import random
import time
from pathlib import Path

import numpy as np
import z3
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import U3Gate
from qiskit.quantum_info import Operator

from distributed_frame_search import native
from post185_depth_walk import profile
from post186_exact_local_phase import collect, extract, replace, phase_signature
from post190_commuting_schedule import records
from post190_window_phase import sliceq
from post258_joint_encoder_schedule import touches


def solve(window, depth, seconds=2, arrivals=None, deadlines=None, seed=0):
    n = window.num_qubits
    assert n >= 2 and depth >= 0
    goal, angles = phase_signature(window)
    terms = sorted(angles)
    arrivals = [0] * n if arrivals is None else list(arrivals)
    deadlines = [depth] * n if deadlines is None else list(deadlines)
    assert len(arrivals) == len(deadlines) == n
    s = z3.Solver()
    s.set(timeout=max(1, int(seconds * 1000)), random_seed=seed)
    basis = [[z3.BitVec(f'b_{t}_{w}', n) for w in range(n)] for t in range(depth + 1)]
    edges = list(itertools.permutations(range(n), 2))
    cx = [[z3.Bool(f'c_{t}_{a}_{b}') for a, b in edges] for t in range(depth)]
    rotations = [[[z3.Bool(f'r_{t}_{w}_{j}') for j in range(len(terms))]
                  for w in range(n)] for t in range(depth)]
    for w in range(n):
        s.add(basis[0][w] == 1 << w, basis[depth][w] == goal[w])
    for t in range(depth):
        for w in range(n):
            incident = [cx[t][i] for i, edge in enumerate(edges) if w in edge]
            incoming = [cx[t][i] for i, (a, b) in enumerate(edges) if b == w]
            actions = incident + rotations[t][w]
            if actions:
                s.add(z3.PbLe([(v, 1) for v in actions], 1))
                if t < arrivals[w] or t + 1 > deadlines[w]:
                    s.add(*[z3.Not(v) for v in actions])
            s.add(z3.Implies(z3.Not(z3.Or(incoming)), basis[t + 1][w] == basis[t][w]))
            for j, mask in enumerate(terms):
                s.add(z3.Implies(rotations[t][w][j], basis[t][w] == mask))
        for i, (a, b) in enumerate(edges):
            s.add(z3.Implies(cx[t][i], basis[t + 1][b] == basis[t][b] ^ basis[t][a]))
    for j in range(len(terms)):
        places = [rotations[t][w][j] for t in range(depth) for w in range(n)]
        s.add(z3.PbEq([(v, 1) for v in places], 1) if places else z3.BoolVal(False))
    started = time.monotonic()
    result = s.check()
    info = dict(status=str(result), bound=depth, wires=n, phases=len(terms),
                solve_seconds=time.monotonic() - started, arrivals=arrivals, deadlines=deadlines)
    if result != z3.sat:
        if result == z3.unknown:
            info['reason'] = s.reason_unknown()
        return None, info
    model = s.model()
    q = QuantumCircuit(n)
    layers = []
    for t in range(depth):
        layer = []
        for i, edge in enumerate(edges):
            if z3.is_true(model.eval(cx[t][i])):
                q.cx(*edge)
                layer.append(['cx', *edge])
        for w in range(n):
            for j, mask in enumerate(terms):
                if z3.is_true(model.eval(rotations[t][w][j])):
                    q.append(U3Gate(0, 0, angles[mask]), [w])
                    layer.append(['phase', w, mask])
        layers.append(layer)
    actual_goal, actual_angles = phase_signature(q)
    assert actual_goal == goal
    assert set(actual_angles) == set(angles)
    assert all(abs(actual_angles[m] - angles[m]) < 1e-9 for m in angles)
    assert q.depth() <= depth
    want, got = Operator(window).data, Operator(q).data
    phase = np.vdot(want, got)
    error = float(np.max(abs(got - phase / abs(phase) * want)))
    assert error < 1e-10
    info.update(layers=layers, operator_error=error, depth=q.depth(), cx=q.count_ops().get('cx', 0))
    return q, info


def proposals(q, widths, seed, count=300):
    rng = random.Random(seed)
    ops = records(q)
    _, critical = profile(q)
    anchors = [i for i in critical if ops[i][0] == 'cx']
    choices = []
    seen = set()
    for attempt in range(count):
        anchor = rng.choice(anchors)
        width = rng.choice(widths)
        wires = set(ops[anchor][1])
        # Grow a connected set near the anchor, avoiding far-away spectators.
        while len(wires) < width:
            neighbors = [w for _, ws, _ in ops[anchor:anchor + 70]
                         if wires.intersection(ws) for w in ws if w not in wires]
            if not neighbors:
                break
            wires.add(rng.choice(neighbors))
        if len(wires) != width:
            continue
        wires = tuple(sorted(wires))
        selected = collect(ops, anchor, wires, limit=160)
        if len(selected) < 7 or len(selected) > 35 or tuple(selected) in seen:
            continue
        seen.add(tuple(selected))
        window = extract(q, selected, wires)
        goal, angles = phase_signature(window)
        if not angles or window.depth() > 16:
            continue
        critical_hits = len(set(selected).intersection(critical))
        choices.append((critical_hits / window.depth(), len(selected), wires, selected, window))
    rng.shuffle(choices)
    choices.sort(key=lambda r: -r[0])
    return choices


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    q = qasm2.load(a.source)
    initial = q.depth()
    best_score = (q.depth(), len(profile(q)[1]))
    history, rows = [], []
    start = time.monotonic()
    tested = set()
    while len(rows) < a.trials and time.monotonic() - start < a.seconds:
        choices = proposals(q, a.widths, a.seed + len(rows))
        choice = next((r for r in choices if (tuple(r[3]), tuple(records(r[4]))) not in tested), None)
        if choice is None:
            break
        _, _, wires, selected, window = choice
        tested.add((tuple(selected), tuple(records(window))))
        if a.context:
            before = touches(sliceq(q, 0, selected[0]))
            suffix = q.copy_empty_like()
            for i in range(selected[0], len(q.data)):
                if i not in set(selected):
                    inst = q.data[i]
                    suffix.append(inst.operation, [q.find_bit(w).index for w in inst.qubits])
            after = touches(suffix.reverse_ops())
            offset = min(before[w] for w in wires)
            arrivals = [before[w] - offset for w in wires]
            deadlines = [q.depth() - after[w] - offset for w in wires]
            bound = max(deadlines)
        else:
            arrivals = deadlines = None
            bound = window.depth() - 1
        if bound > 24 or bound < 0:
            continue
        replacement, info = solve(window, bound, a.per_window, arrivals, deadlines,
                                  seed=a.seed + len(rows))
        row = dict(index=len(rows), wires=wires, selected=selected, original_depth=window.depth(), search=info)
        if replacement is not None:
            c = native(replace(q, selected, replacement, wires))
            score = (c.depth(), len(profile(c)[1]))
            row.update(full_depth=c.depth(), full_cx=c.count_ops().get('cx', 0), critical=score[1])
            # Save useful isolated gains too, so exact global scheduling can
            # assess them later even when greedy full depth regresses slightly.
            if c.depth() <= initial + 3:
                path = a.outdir / f'candidate{len(rows)}_d{c.depth()}.qasm'
                path.write_text(qasm2.dumps(c))
                from exhaustive_verify import exhaustive
                exhaustive(path)
                row['path'] = str(path)
            if score < best_score:
                q, best_score = c, score
                history.append(row.copy())
                tested.clear()
                print('accepted', best_score, flush=True)
        rows.append(row)
        print('window', len(rows), len(wires), window.depth(), info['status'], row.get('full_depth'), flush=True)
        report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                      initial_depth=initial, best_depth=q.depth(), rows=rows, history=history,
                      seconds=time.monotonic() - start, context=a.context, widths=a.widths)
        (a.outdir / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return q


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/185/two_stage_185.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=120)
    p.add_argument('--trials', type=int, default=60)
    p.add_argument('--per-window', type=float, default=2)
    p.add_argument('--widths', type=int, nargs='+', default=[5, 6, 7])
    p.add_argument('--seed', type=int, default=185516)
    p.add_argument('--context', action='store_true')
    run(p.parse_args())
