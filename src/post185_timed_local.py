"""Three/four-wire phase synthesis with per-wire arrival times and deadlines.

Unlike minimum isolated depth, this finite search asks whether a replacement
can fit the actual surrounding critical path. Waiting and extra CX are allowed.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random
import time

from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import U3Gate
from qiskit.quantum_info import Operator
from distributed_frame_search import native
from post185_depth_walk import profile
from post186_exact_local_phase import collect, extract, replace, phase_signature
from post190_commuting_schedule import records
from post190_window_phase import sliceq
from post258_joint_encoder_schedule import touches


def solve_window(window, arrival, departure, deadline, state_limit=160000):
    goal, angles = phase_signature(window)
    required = sum(1 << m for m in angles)
    n = window.num_qubits
    assert n in (3, 4)
    start = (tuple(1 << w for w in range(n)), 0)
    states = {start: ()}
    visited = 0
    for t in range(min(arrival), deadline-min(departure)+1):
        next_states = {}
        legal = {w for w in range(n) if arrival[w] <= t and t+1+departure[w] <= deadline}
        single_pairs = list(itertools.permutations(sorted(legal), 2))
        cx_layers = [(pair,) for pair in single_pairs]
        if len(legal) == 4:
            cx_layers.extend((first, second) for i, first in enumerate(single_pairs)
                             for second in single_pairs[i+1:] if set(first).isdisjoint(second))
        for (basis, done), path in states.items():
            visited += 1
            if visited > state_limit:
                return None, dict(status='state_limit', visited=visited)
            if (basis, done) == (goal, required):
                result = QuantumCircuit(n)
                for layer, phases, old_basis in path:
                    for w in phases:
                        result.append(U3Gate(0, 0, angles[old_basis[w]]), [w])
                    for pair in layer:
                        result.cx(*pair)
                return result, dict(status='found', visited=visited, deadline=deadline)
            available = tuple(w for w in legal if required >> basis[w] & 1 and not done >> basis[w] & 1)
            choices = [((), available), ((), ())]
            for layer in cx_layers:
                used = {w for pair in layer for w in pair}
                choices.append((layer, tuple(w for w in available if w not in used)))
            for layer, phases in choices:
                new_done = done
                for w in phases:
                    new_done |= 1 << basis[w]
                new_basis = list(basis)
                for pair in layer:
                    new_basis[pair[1]] ^= new_basis[pair[0]]
                state = (tuple(new_basis), new_done)
                # Equivalent states at the same time have identical remaining
                # legal moves, so retaining one history is exact here.
                if state not in next_states:
                    next_states[state] = path+((layer, phases, basis),)
        states = next_states
    return None, dict(status='infeasible_in_local_model', visited=visited, deadline=deadline)


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    q = qasm2.load(a.source)
    rng = random.Random(a.seed)
    best, critical = profile(q)
    critical_count = len(critical)
    rows, history, seen = [], [], set()
    started = time.monotonic()
    attempted = 0
    while len(rows) < a.trials and time.monotonic()-started < a.seconds:
        ops = records(q)
        _, critical = profile(q)
        anchor = rng.choice([i for i in critical if ops[i][0]=='cx'])
        pair = set(ops[anchor][1])
        nearby = {w for op in ops[anchor:anchor+80] for w in op[1]}-pair
        if not nearby:
            continue
        if len(nearby) < a.width-2:
            continue
        wires = tuple(sorted(pair | set(rng.sample(sorted(nearby),a.width-2))))
        selected = collect(ops, anchor, wires, limit=220)
        attempted += 1
        if len(selected) < 4:
            continue
        key = (tuple(ops[i] for i in selected), selected[0])
        if key in seen:
            continue
        seen.add(key)
        window = extract(q, selected, wires)
        before = touches(sliceq(q, 0, selected[0]))
        suffix = q.copy_empty_like()
        selected_set = set(selected)
        for i in range(selected[0], len(q.data)):
            if i not in selected_set:
                inst = q.data[i]
                suffix.append(inst.operation, [q.find_bit(w).index for w in inst.qubits])
        after = touches(suffix.reverse_ops())
        # If an unaffected path already takes best layers, this replacement
        # alone cannot improve the current serialization; still allow neutral
        # contexts to expose a different global schedule afterward.
        arrival = [before[w] for w in wires]
        departure = [after[w] for w in wires]
        shift = min(arrival)
        arrival = [v-shift for v in arrival]
        target = best-(0 if a.neutral else 1)-shift
        replacement, info = solve_window(window, arrival, departure, target, a.state_limit)
        row = dict(wires=wires, selected=selected, arrival=arrival, departure=departure, search=info)
        if replacement is not None:
            assert Operator(window).equiv(Operator(replacement),atol=1e-10,rtol=0)
            candidate = native(replace(q, selected, replacement, wires))
            row.update(depth=candidate.depth(),cx=candidate.count_ops().get('cx',0))
            candidate_depth, candidate_critical = profile(candidate)
            if (candidate_depth, len(candidate_critical)) < (best, critical_count):
                q = candidate
                best = q.depth()
                critical_count = len(candidate_critical)
                path = a.outdir/f'candidate{len(rows)}_d{best}_cx{q.count_ops().get("cx",0)}.qasm'
                path.write_text(qasm2.dumps(q))
                from exhaustive_verify import exhaustive
                exhaustive(path)
                row['path'] = str(path)
                history.append(row.copy())
                print('IMPROVED depth/critical',best,critical_count,flush=True)
                seen.clear()
        rows.append(row)
        if len(rows)%10==0:
            print('timed windows',len(rows),'best depth',best,'last',info['status'],flush=True)
        report = dict(source=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                      best_depth=best,critical_count=critical_count,neutral=a.neutral,width=a.width,
                      attempts=attempted,windows=len(rows),seconds=time.monotonic()-started,
                      history=history,rows=rows)
        (a.outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=Path('artifacts/185/two_stage_185.qasm'))
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--trials',type=int,default=100)
    p.add_argument('--seconds',type=float,default=90)
    p.add_argument('--state-limit',type=int,default=160000)
    p.add_argument('--seed',type=int,default=1854)
    p.add_argument('--neutral',action='store_true')
    p.add_argument('--width',type=int,choices=[3,4],default=3)
    run(p.parse_args())
