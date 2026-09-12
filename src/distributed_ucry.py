"""Exact multi-output Ry lookup via parity phases hosted on data and outputs.

Split six address bits into three low controls and three high variables.
The 24 high/output parities are partitioned into four invertible bases on six
wires. Each basis hosts six simultaneous three-control Rz sweeps. The full
linear basis is restored, and Rx conjugation converts Z back to Y on outputs.
All identities hold for arbitrary inputs, including arbitrary output qubits.
"""
import argparse
import functools
import itertools
import json
import math
import random
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.synthesis.linear import synth_cnot_count_full_pmh


def rank(rows):
    piv = {}
    for row in rows:
        while row:
            i = row.bit_length()-1
            if i in piv:
                row ^= piv[i]
            else:
                piv[i] = row
                break
    return len(piv)


def coordinates(value, basis):
    piv = {}
    for j, row in enumerate(basis):
        comb = 1 << j
        while row:
            i = row.bit_length()-1
            if i in piv:
                a, b = piv[i]
                row ^= a
                comb ^= b
            else:
                piv[i] = row, comb
                break
    ans = 0
    while value:
        i = value.bit_length()-1
        row, comb = piv[i]
        value ^= row
        ans ^= comb
    return ans


@functools.lru_cache(maxsize=20000)
def change_basis(before, after):
    n = len(before)
    rows = [coordinates(row, before) for row in after]
    matrix = np.array([[(row >> j) & 1 for j in range(n)] for row in rows], dtype=bool)
    candidates = [synth_cnot_count_full_pmh(matrix, section_size=s) for s in (1, 2, 3)]
    q = min(candidates, key=lambda c: (c.depth(), c.size()))
    actual = list(before)
    for inst in q.data:
        a, b = [q.find_bit(v).index for v in inst.qubits]
        assert inst.operation.name == 'cx'
        actual[b] ^= actual[a]
    assert actual == list(after), (actual, after)
    return q


def bases(seed):
    rng = random.Random(seed)
    masks = [h | (1 << (3+t)) for t in range(3) for h in range(8)]
    for _ in range(10000):
        remaining = masks.copy()
        rng.shuffle(remaining)
        groups = []
        for _ in range(4):
            group = []
            for v in remaining:
                if rank(group+[v]) > len(group):
                    group.append(v)
                    if len(group) == 6:
                        break
            if len(group) != 6:
                break
            groups.append(group)
            remaining = [v for v in remaining if v not in group]
        if len(groups) == 4:
            return groups
    raise RuntimeError('basis partition not found')


def walsh(tables):
    a = np.asarray(tables, float).copy()
    h = 1
    while h < a.shape[1]:
        for i in range(0, a.shape[1], 2*h):
            lo = a[:, i:i+h].copy()
            hi = a[:, i+h:i+2*h].copy()
            a[:, i:i+h] = lo+hi
            a[:, i+h:i+2*h] = lo-hi
        h *= 2
    return a/a.shape[1]


def ucry(angle_tables, outputs, controls, seed=0, high=None, groups=None):
    assert len(controls) == 6 and len(outputs) == 3
    rng = random.Random(seed)
    high = list(high) if high is not None else rng.sample(range(6), 3)
    low = [i for i in range(6) if i not in high]
    hosts = [controls[i] for i in high] + list(outputs)
    lows = [controls[i] for i in low]
    groups = groups if groups is not None else bases(seed)
    co = walsh(angle_tables)
    q = QuantumCircuit(max(list(outputs)+list(controls))+1)
    for t in outputs:
        q.rx(math.pi/2, t)
    current = tuple(1 << i for i in range(6))
    for group in groups:
        after = tuple(group)
        q.compose(change_basis(current, after), hosts, inplace=True)
        # Two cohorts of three hosts use cyclically shifted Gray controls.
        orders = [low[(i % 3):]+low[:(i % 3)] for i in range(6)]
        for step in range(8):
            gray = step ^ (step >> 1)
            pos = ((step+1) & -(step+1)).bit_length()-1 if step < 7 else 2
            for j, parity in enumerate(group):
                target = (parity >> 3).bit_length()-1
                hmask = sum(((parity >> k) & 1) << high[k] for k in range(3))
                lmask = sum(((gray >> k) & 1) << orders[j][k] for k in range(3))
                theta = float(co[target, hmask | lmask])
                if abs(theta) > 1e-14:
                    q.rz(theta, hosts[j])
                q.cx(controls[orders[j][pos]], hosts[j])
        current = after
    q.compose(change_basis(current, tuple(1 << i for i in range(6))), hosts, inplace=True)
    for t in outputs:
        q.rx(-math.pi/2, t)
    return q


def emit_sparse_sweeps(q, group, co, high, low, hosts, controls, rng):
    """Independent low-control parity walks, interleaved by wire availability."""
    jobs = []
    for parity in group:
        target = (parity >> 3).bit_length()-1
        hmask = sum(((parity >> k) & 1) << high[k] for k in range(3))
        coeff = {m: float(co[target, hmask | sum(((m >> k) & 1) << low[k] for k in range(3))])
                 for m in range(8)}
        required = [m for m in range(8) if abs(coeff[m]) > 1e-14]
        choices = []
        for order in itertools.permutations(range(3)):
            walk = [sum((((j ^ (j >> 1)) >> k) & 1) << order[k] for k in range(3))
                    for j in range(8)]
            selected = [m for m in walk if m in required]
            for sequence in (selected, list(reversed(selected))):
                ops = []
                current = 0
                for mask in sequence:
                    for k in order:
                        if (current ^ mask) >> k & 1:
                            ops.append(('cx', controls[low[k]]))
                    ops.append(('rz', coeff[mask]))
                    current = mask
                for k in order:
                    if current >> k & 1:
                        ops.append(('cx', controls[low[k]]))
                choices.append(ops)
        shortest = min(map(len, choices))
        jobs.append(rng.choice([s for s in choices if len(s) == shortest]))
    positions = [0]*6
    while any(positions[i] < len(jobs[i]) for i in range(6)):
        used = set()
        ready = [i for i in range(6) if positions[i] < len(jobs[i])]
        # Longest remaining host chain first; randomized ties give alternative
        # valid schedules without changing a phase or a parity.
        rng.shuffle(ready)
        ready.sort(key=lambda i: len(jobs[i])-positions[i], reverse=True)
        for i in ready:
            kind, value = jobs[i][positions[i]]
            if kind == 'cx':
                if value in used:
                    continue
                q.cx(value, hosts[i])
                used.add(value)
            else:
                q.rz(value, hosts[i])
            positions[i] += 1


def structured_ucry(angle_tables, outputs, controls, seed=0, high=None, sparse=False, open_walk=False):
    """Four structured bases with three-layer exact transitions.

    Hosts are (x_i XOR t_i XOR shift_i, t_i XOR shift_i), i=0,1,2.
    Each shift walks the other two high bits in Gray order. Uncopying the
    t_i restores all three x_i in one layer; a cyclic high-to-output CX layer
    updates all shifts; recopying takes one more layer. Generic Gaussian
    lowering can miss this simple three-layer transition.
    """
    assert len(controls) == 6 and len(outputs) == 3
    assert len(set(list(controls)+list(outputs))) == 9
    assert not (sparse and open_walk), 'Sparse and carried Gray walks are separate constructions'
    rng = random.Random(seed)
    high = list(high) if high is not None else rng.sample(range(6), 3)
    low = [i for i in range(6) if i not in high]
    rng.shuffle(low)
    hosts = [controls[i] for i in high] + list(outputs)
    co = walsh(angle_tables)
    q = QuantumCircuit(max(list(outputs)+list(controls))+1)
    for t in outputs:
        q.rx(math.pi/2, t)
    for i in range(3):
        q.cx(outputs[i], controls[high[i]])
    for stage in range(4):
        gray_high = stage ^ (stage >> 1)
        shifts = [sum(((gray_high >> k) & 1) << ((i+k+1) % 3) for k in range(2))
                  for i in range(3)]
        group = [(1 << (3+i)) ^ (1 << i) ^ shifts[i] for i in range(3)]
        group += [(1 << (3+i)) ^ shifts[i] for i in range(3)]
        if sparse:
            emit_sparse_sweeps(q, group, co, high, low, hosts, controls, rng)
        else:
            orders = [low[(i % 3):]+low[:(i % 3)] for i in range(6)]
            for step in range(8):
                gray = step ^ (step >> 1)
                pos = ((step+1) & -(step+1)).bit_length()-1 if step < 7 else 2
                for j, parity in enumerate(group):
                    target = (parity >> 3).bit_length()-1
                    hmask = sum(((parity >> k) & 1) << high[k] for k in range(3))
                    visited = gray ^ (4 if open_walk and stage % 2 else 0)
                    lmask = sum(((visited >> k) & 1) << orders[j][k] for k in range(3))
                    theta = float(co[target, hmask | lmask])
                    if abs(theta) > 1e-14:
                        q.rz(theta, hosts[j])
                    if not open_walk or step < 7:
                        q.cx(controls[orders[j][pos]], hosts[j])
        for i in range(3):
            q.cx(outputs[i], controls[high[i]])
        if stage < 3:
            next_gray = (stage+1) ^ ((stage+1) >> 1)
            changed = (gray_high ^ next_gray).bit_length()-1
            for i in range(3):
                q.cx(controls[high[(i+changed+1) % 3]], outputs[i])
            for i in range(3):
                q.cx(outputs[i], controls[high[i]])
        else:
            for i in range(3):
                for k in range(2):
                    if gray_high >> k & 1:
                        q.cx(controls[high[(i+k+1) % 3]], outputs[i])
    for t in outputs:
        q.rx(-math.pi/2, t)
    return q


def verify_component(circuit, tables):
    from qiskit.quantum_info import Operator
    assert circuit.num_qubits == 9
    op = Operator(qasm2.loads(qasm2.dumps(circuit))).data
    expected = np.zeros((512, 512), complex)
    for address in range(64):
        block = np.array([[1.0]])
        for bit in reversed(range(3)):
            theta = tables[bit][address]
            c, s = np.cos(theta/2), np.sin(theta/2)
            block = np.kron(block, [[c, -s], [s, c]])
        idx = [address+64*t for t in range(8)]
        expected[np.ix_(idx, idx)] = block
    overlap = np.vdot(expected, op)
    phase = overlap/abs(overlap)
    error = float(np.max(np.abs(op-phase*expected)))
    assert error < 1e-10, error
    return error


if __name__ == '__main__':
    from level_oracle import LEVEL, code_of, angle_table, TRIPLE_DEFAULT
    parser = argparse.ArgumentParser()
    parser.add_argument('--seeds', type=int, default=20)
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()
    assert not args.outdir.exists()
    args.outdir.mkdir(parents=True)
    _, targets = code_of(TRIPLE_DEFAULT, LEVEL['u1'])
    tables = angle_table(targets)
    rows = []
    best = None
    for seed in range(args.seeds):
        raw = ucry(tables, [6, 7, 8], list(range(6)), seed)
        native = transpile(raw, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                           optimization_level=3, seed_transpiler=0)
        row = dict(seed=seed, depth=native.depth(), cx=native.count_ops().get('cx', 0))
        rows.append(row)
        if best is None or (row['depth'], row['cx']) < (best['depth'], best['cx']):
            row['error'] = verify_component(native, tables)
            best = row
            (args.outdir/f'component_seed{seed}.qasm').write_text(qasm2.dumps(native))
            print('best', row, flush=True)
    (args.outdir/'report.json').write_text(json.dumps(dict(best=best, rows=rows), indent=2)+'\n')
