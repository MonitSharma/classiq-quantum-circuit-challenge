"""Exact three-wire CNOT/phase resynthesis inside the complete native oracle.

The finite search tracks a reversible GF(2) basis and which phase parities
have been emitted. It finds minimum synchronous layers in this restricted
gate set, preserving the entire local operator up to one global phase.
"""
import argparse
from collections import deque
from functools import lru_cache
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import time

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import U3Gate
from qiskit.quantum_info import Operator
from distributed_frame_search import native
from post190_commuting_schedule import records


def collect(ops, anchor, wires, limit=180):
    """Collect a convex region; every skipped gate commutes with later picks."""
    selected = []
    allowed = set(wires)
    blocked = set()
    for i in range(anchor, min(len(ops), anchor+limit)):
        name, ws, params = ops[i]
        ws = set(ws)
        if not ws & allowed:
            continue
        diagonal = name == 'cx' or (name == 'u3' and abs(math.sin(params[0]/2)) < 1e-12)
        if ws <= allowed and not ws & blocked and diagonal:
            selected.append(i)
        else:
            blocked.update(ws & allowed)
        if blocked >= allowed:
            break
    return selected


def phase_signature(q):
    basis = [1 << w for w in range(q.num_qubits)]
    angles = {}
    for name, ws, params in records(q):
        if name == 'cx':
            basis[ws[1]] ^= basis[ws[0]]
        else:
            assert abs(math.sin(params[0]/2)) < 1e-12
            m = basis[ws[0]]
            angles[m] = angles.get(m, 0.) + params[1] + params[2]
    angles = {m: (v+math.pi) % (2*math.pi)-math.pi for m, v in angles.items()}
    angles = {m: v for m, v in angles.items() if abs(v) > 1e-11}
    return tuple(basis), angles


@lru_cache(maxsize=8192)
def shortest(goal, required):
    start = ((1, 2, 4), 0)
    pending = deque([start])
    parent = {start: None}
    target = (goal, required)
    pairs = list(itertools.permutations(range(3), 2))
    while pending:
        state = pending.popleft()
        if state == target:
            layers = []
            while parent[state] is not None:
                prev, layer = parent[state]
                layers.append(layer)
                state = prev
            return tuple(reversed(layers))
        basis, done = state
        available = [w for w in range(3) if required >> basis[w] & 1 and not done >> basis[w] & 1]
        # A CX may share its layer with a phase on the remaining wire.
        choices = []
        if available:
            choices.append((None, tuple(available)))
        for a, b in pairs:
            spectator = 3-a-b
            choices.append(((a, b), (spectator,) if spectator in available else ()))
        for pair, phase_wires in choices:
            new_done = done
            for w in phase_wires:
                new_done |= 1 << basis[w]
            new_basis = list(basis)
            if pair:
                a, b = pair
                new_basis[b] ^= new_basis[a]
            nxt = (tuple(new_basis), new_done)
            if nxt not in parent:
                parent[nxt] = (state, (pair, phase_wires))
                pending.append(nxt)
    raise AssertionError('Finite parity network unexpectedly unreachable')


def synthesize(window):
    goal, angles = phase_signature(window)
    layers = shortest(goal, sum(1 << m for m in angles))
    basis = [1, 2, 4]
    q = QuantumCircuit(3)
    for pair, phase_wires in layers:
        for w in phase_wires:
            q.append(U3Gate(0, 0, angles[basis[w]]), [w])
        if pair:
            a, b = pair
            q.cx(a, b)
            basis[b] ^= basis[a]
    assert tuple(basis) == goal
    return q


def extract(q, selected, wires):
    qlocal = QuantumCircuit(len(wires))
    locations = {w: i for i, w in enumerate(wires)}
    for i in selected:
        inst = q.data[i]
        qlocal.append(inst.operation, [locations[q.find_bit(w).index] for w in inst.qubits])
    return qlocal


def replace(q, selected, replacement, wires):
    result = QuantumCircuit(q.num_qubits, global_phase=q.global_phase)
    selected_set = set(selected)
    for i, inst in enumerate(q.data):
        if i == selected[0]:
            result.compose(replacement, wires, inplace=True)
        if i not in selected_set:
            result.append(inst.operation, [q.find_bit(w).index for w in inst.qubits])
    return result


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    q = qasm2.load(a.source)
    rng = random.Random(a.seed)
    initial = (q.depth(), q.count_ops().get('cx', 0), len(q.data))
    best = initial
    history = []
    attempted = 0
    rewritten = 0
    start = time.monotonic()
    seen = set()
    while attempted < a.trials and time.monotonic()-start < a.seconds:
        ops = records(q)
        cx_indices = [i for i, op in enumerate(ops) if op[0] == 'cx']
        anchor = rng.choice(cx_indices)
        touched = ops[anchor][1]
        # Pick a nearby interaction so the region can include a useful network.
        nearby = {w for op in ops[anchor:anchor+70] for w in op[1]} - set(touched)
        if not nearby:
            continue
        wires = tuple(sorted((*touched, rng.choice(sorted(nearby)))))
        selected = collect(ops, anchor, wires)
        attempted += 1
        if len(selected) < 3:
            continue
        key = tuple(ops[i] for i in selected)
        if key in seen:
            continue
        seen.add(key)
        old = extract(q, selected, wires)
        candidate = synthesize(old)
        if (candidate.depth(), candidate.count_ops().get('cx', 0), len(candidate.data)) >= (old.depth(), old.count_ops().get('cx', 0), len(old.data)):
            continue
        assert Operator(old).equiv(Operator(candidate), atol=1e-10, rtol=0)
        full = native(replace(q, selected, candidate, wires))
        score = (full.depth(), full.count_ops().get('cx', 0), len(full.data))
        rewritten += 1
        if score < best:
            q = full
            best = score
            path = a.outdir/f'candidate{len(history)}_d{score[0]}_cx{score[1]}.qasm'
            path.write_text(qasm2.dumps(q))
            from exhaustive_verify import exhaustive
            exhaustive(path)
            history.append(dict(attempt=attempted, depth=score[0], cx=score[1], gates=score[2],
                                path=str(path), wires=wires, selected=selected,
                                replacement=qasm2.dumps(candidate)))
            print('IMPROVED', best, 'attempt', attempted, flush=True)
            seen.clear()
        if rewritten % 25 == 0:
            print('progress', attempted, rewritten, best, flush=True)
    report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                  initial=initial, best=best, attempts=attempted, replacements_scored=rewritten,
                  seconds=time.monotonic()-start, cache=str(shortest.cache_info()), history=history)
    (a.outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print({k: v for k, v in report.items() if k != 'history'}, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/186/two_stage_186.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=80)
    p.add_argument('--trials', type=int, default=5000)
    p.add_argument('--seed', type=int, default=186)
    run(p.parse_args())
