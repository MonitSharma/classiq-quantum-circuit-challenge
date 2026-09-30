"""CZ-frame reordering and explicit CX-direction search for total native depth.

Each CZ may lower as H(b) CX(a,b) H(b) or H(a) CX(b,a) H(a).
Fuse all adjacent one-qubit matrices exactly while scoring orientations. This
can alter the native gate list, not merely reorder the existing CNOTs.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import time
from functools import lru_cache

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import U3Gate
from qiskit.synthesis import OneQubitEulerDecomposer

from distributed_frame_search import native
from post190_commuting_schedule import records, schedule, reordered

H = np.array([[1, 1], [1, -1]], complex) / math.sqrt(2)
I = np.eye(2, dtype=complex)
DECOMPOSE = OneQubitEulerDecomposer('U3')


def scalar(u):
    return abs(u[0, 1]) + abs(u[1, 0]) + abs(u[0, 0] - u[1, 1]) < 1e-10


def append_matrix(q, u, wire):
    if scalar(u):
        q.global_phase += float(np.angle(u[0, 0]))
        return
    theta, phi, lam, phase = DECOMPOSE.angles_and_phase(u)
    q.append(U3Gate(theta, phi, lam), [wire])
    q.global_phase += float(phase)


def to_cz(q):
    out = QuantumCircuit(q.num_qubits, global_phase=q.global_phase)
    pending = [I.copy() for _ in range(q.num_qubits)]
    orientations = []
    for name, ws, params in records(q):
        if name == 'u3':
            pending[ws[0]] = U3Gate(*params).to_matrix() @ pending[ws[0]]
        else:
            assert name == 'cx'
            a, b = ws
            pending[b] = H @ pending[b]
            for w in ws:
                append_matrix(out, pending[w], w)
                pending[w] = I.copy()
            out.cz(a, b)
            pending[b] = H.copy()
            orientations.append(0)
    for w in range(q.num_qubits):
        append_matrix(out, pending[w], w)
    return out, orientations


def prepared(q):
    return [(name, ws, U3Gate(*params).to_matrix() if name == 'u3' else None)
            for name, ws, params in records(q)]


def lower(q, ops, choices, emit=False):
    pending = [I.copy() for _ in range(q.num_qubits)]
    times = [0] * q.num_qubits
    out = QuantumCircuit(q.num_qubits, global_phase=q.global_phase) if emit else None
    single_count = 0

    def flush(w):
        nonlocal single_count
        if not scalar(pending[w]):
            times[w] += 1
            single_count += 1
        if emit:
            append_matrix(out, pending[w], w)
        pending[w] = I.copy()

    j = 0
    for name, ws, matrix in ops:
        if name == 'u3':
            pending[ws[0]] = matrix @ pending[ws[0]]
        else:
            assert name == 'cz'
            a, b = ws if choices[j] == 0 else tuple(reversed(ws))
            j += 1
            pending[b] = H @ pending[b]
            flush(a)
            flush(b)
            times[a] = times[b] = max(times[a], times[b]) + 1
            if emit:
                out.cx(a, b)
            pending[b] = H.copy()
    assert j == len(choices)
    for w in range(q.num_qubits):
        flush(w)
    return (max(times), single_count), out


@lru_cache(maxsize=200000)
def commutes(a, b):
    na, wa, pa = a
    nb, wb, pb = b
    if not set(wa).intersection(wb) or na == nb == 'cz':
        return True
    if na == nb == 'u3':
        x, y = U3Gate(*pa).to_matrix(), U3Gate(*pb).to_matrix()
        return np.max(abs(x @ y - y @ x)) < 1e-12
    if na == 'u3':
        return commutes(b, a)
    assert na == 'cz' and nb == 'u3'
    u = U3Gate(*pb).to_matrix()
    return abs(u[0, 1]) + abs(u[1, 0]) < 1e-12


def graph(q):
    ops = records(q)
    succ = [set() for _ in ops]
    seen = [[] for _ in range(q.num_qubits)]
    for j, op in enumerate(ops):
        for i in {i for w in op[1] for i in seen[w]}:
            if not commutes(ops[i], op):
                succ[i].add(j)
        for w in op[1]:
            seen[w].append(j)
    reach = [0] * len(ops)
    reduced = [[] for _ in ops]
    for i in reversed(range(len(ops))):
        for j in sorted(succ[i]):
            if not (reach[i] >> j & 1):
                reduced[i].append(j)
                reach[i] |= (1 << j) | reach[j]
    pred = [[] for _ in ops]
    for i, js in enumerate(reduced):
        for j in js:
            pred[j].append(i)
    return ops, reduced, pred


def exact_orientations(q, seconds=10, hint=None):
    """Choose all CZ-to-CX directions jointly for a fixed wire ordering.

    Between consecutive CZ events on a wire, the single-qubit product is
    H(next_target) M H(previous_target). Its native cost is zero or one. These
    four exact matrix cases encode the timing edge in a CP-SAT model.
    """
    from ortools.sat.python import cp_model
    ops = prepared(q)
    events = [ws for name, ws, _ in ops if name == 'cz']
    pending = [I.copy() for _ in range(q.num_qubits)]
    previous = [None] * q.num_qubits
    segments = []
    j = 0
    for name, ws, matrix in ops:
        if name == 'u3':
            pending[ws[0]] = matrix @ pending[ws[0]]
        else:
            for w in ws:
                segments.append((w, previous[w], j, pending[w]))
                pending[w] = I.copy()
                previous[w] = j
            j += 1
    for w in range(q.num_qubits):
        segments.append((w, previous[w], None, pending[w]))
    hint = [0] * len(events) if hint is None else hint
    upper = lower(q, ops, hint)[0][0]
    model = cp_model.CpModel()
    directions = [model.new_bool_var(f'd{i}') for i in range(len(events))]
    times = [model.new_int_var(0, upper - 1, f't{i}') for i in range(len(events))]
    span = model.new_int_var(0, upper, 'depth')
    for i, d in enumerate(directions):
        model.add_hint(d, hint[i])
    for idx, (w, prev, nxt, matrix) in enumerate(segments):
        ids = [i for i in (prev, nxt) if i is not None]
        cases = []
        for vals in __import__('itertools').product((0, 1), repeat=len(ids)):
            assignment = dict(zip(ids, vals))
            value = matrix.copy()
            if prev is not None and w == events[prev][1 - assignment[prev]]:
                value = value @ H
            if nxt is not None and w == events[nxt][1 - assignment[nxt]]:
                value = H @ value
            cases.append((*vals, int(not scalar(value))))
        cost = model.new_bool_var(f'g{idx}')
        if ids:
            model.add_allowed_assignments([directions[i] for i in ids] + [cost], cases)
        else:
            model.add(cost == cases[0][-1])
        left = 0 if prev is None else times[prev] + 1
        right = span if nxt is None else times[nxt]
        model.add(right >= left + cost)
    model.minimize(span)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 185
    status = solver.solve(model)
    info = dict(status=solver.status_name(status), initial_depth=upper,
                lower_bound=solver.best_objective_bound, seconds=solver.wall_time)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, info
    choices = [solver.value(d) for d in directions]
    score, circuit = lower(q, ops, choices, emit=True)
    assert score[0] <= solver.value(span)
    info.update(choices=choices, depth=score[0], objective=solver.value(span))
    return circuit, info


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    source = qasm2.load(a.source)
    cz, _ = to_cz(source)
    (a.outdir / 'cz_frame.qasm').write_text(qasm2.dumps(cz))
    ops, succ, pred = graph(cz)
    rng = random.Random(a.seed)
    rows, history = [], []
    best = source.depth()
    start = time.monotonic()
    for ordering in range(a.orderings):
        if time.monotonic() - start >= a.seconds:
            break
        layers = schedule(ops, succ, pred, ordering) if ordering else [[i] for i in range(len(ops))]
        current = reordered(cz, layers, pred)
        prepared_ops = prepared(current)
        choices = [0] * current.count_ops().get('cz', 0)
        score, _ = lower(current, prepared_ops, choices)
        baseline = score[0]
        attempts = accepted = 0
        for attempt in range(a.moves):
            if time.monotonic() - start >= a.seconds:
                break
            # Include pairs to cross cases where flipping one direction first
            # introduces a Hadamard that cancels after its neighbor flips.
            indices = rng.sample(range(len(choices)), 1 if attempt % 3 else 2)
            for j in indices:
                choices[j] ^= 1
            new, _ = lower(current, prepared_ops, choices)
            attempts += 1
            if new[0] < score[0] or (new[0] == score[0] and new[1] <= score[1]):
                score = new
                accepted += 1
            else:
                for j in indices:
                    choices[j] ^= 1
        _, candidate = lower(current, prepared_ops, choices, emit=True)
        assert candidate.depth() == score[0]
        candidate = native(candidate)
        path = a.outdir / f'candidate{ordering}_d{candidate.depth()}.qasm'
        path.write_text(qasm2.dumps(candidate))
        row = dict(ordering=ordering, initial_depth=baseline, symbolic_depth=score[0],
                   depth=candidate.depth(), cx=candidate.count_ops().get('cx', 0),
                   attempts=attempts, accepted=accepted, path=str(path), choices=choices,
                   order=[i for layer in layers for i in layer])
        from exhaustive_verify import exhaustive
        exhaustive(path)
        rows.append(row)
        if candidate.depth() < best:
            best = candidate.depth()
            history.append(row.copy())
        print('CZ orientation', ordering, baseline, score, candidate.depth(), flush=True)
        report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                      best_depth=best, rows=rows, history=history, seconds=time.monotonic() - start)
        (a.outdir / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/185/two_stage_185.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--orderings', type=int, default=8)
    p.add_argument('--moves', type=int, default=1200)
    p.add_argument('--seconds', type=float, default=120)
    p.add_argument('--seed', type=int, default=185916)
    run(p.parse_args())
