"""Depth-budgeted destructive Boolean phase search on 18 physical wires.

Each layer is a matching of CX or relative-phase CCX gates. The phase target
may be any affine combination of the midpoint wires. Approximate checkpoints
are search data, NEVER oracle candidates. Only exact solutions are emitted.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import z3
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import U3Gate

from destructive_semantic_search import (
    ALL_ONES, TARGET, initial_wire_truth_tables,
)


def validate(layers):
    for layer in layers:
        assert layer['kind'] in ('x', 'cx', 'ccx')
        arity = {'x': 1, 'cx': 2, 'ccx': 3}[layer['kind']]
        wires = [w for gate in layer['gates'] for w in gate]
        assert all(len(gate) == arity for gate in layer['gates'])
        assert all(0 <= w < 18 for w in wires)
        assert len(wires) == len(set(wires)), 'A physical layer must be disjoint'


def semantic(layers):
    validate(layers)
    wires = list(initial_wire_truth_tables())
    for layer in layers:
        for gate in layer['gates']:
            if layer['kind'] == 'x':
                wires[gate[0]] ^= ALL_ONES
            elif layer['kind'] == 'cx':
                a, t = gate
                wires[t] ^= wires[a]
            else:
                a, b, t = gate
                wires[t] ^= wires[a] & wires[b]
    return tuple(wires)


def parity(wires, mask, constant=0):
    value = ALL_ONES if constant else 0
    for i, wire in enumerate(wires):
        if mask >> i & 1:
            value ^= wire
    return value


def nearest_affine(wires, target=TARGET):
    """Exact nearest parity via a Walsh transform of the midpoint histogram.

    For mask m, transform[m] = sum_x (-1)^(target(x) XOR m.midpoint(x)).
    Thus (4096 - abs(transform[m]))/2 is its best distance, allowing a constant.
    Unlike a Gaussian remainder this is independent of the elimination basis.
    """
    n = len(wires)
    words = np.zeros(4096, dtype=np.int32)
    for i, wire in enumerate(wires):
        bits = np.unpackbits(np.frombuffer(wire.to_bytes(512, 'little'), dtype=np.uint8), bitorder='little')
        words |= bits.astype(np.int32) << i
    target_bits = np.unpackbits(np.frombuffer(target.to_bytes(512, 'little'), dtype=np.uint8), bitorder='little')
    spectrum = np.bincount(words, weights=1 - 2 * target_bits.astype(np.int32), minlength=1 << n).astype(np.int32)
    stride = 1
    while stride < len(spectrum):
        blocks = spectrum.reshape(-1, 2 * stride)
        left = blocks[:, :stride].copy()
        right = blocks[:, stride:].copy()
        blocks[:, :stride] = left + right
        blocks[:, stride:] = left - right
        stride *= 2
    mask = int(np.argmax(np.abs(spectrum)))
    correlation = int(spectrum[mask])
    return {'distance': (4096 - abs(correlation)) // 2,
            'mask': mask, 'constant': int(correlation < 0)}


def margolus():
    q = QuantumCircuit(3)
    q.append(U3Gate(math.pi / 4, 0, 0), [2])
    q.cx(1, 2)
    q.append(U3Gate(math.pi / 4, 0, 0), [2])
    q.cx(0, 2)
    q.append(U3Gate(-math.pi / 4, 0, 0), [2])
    q.cx(1, 2)
    q.append(U3Gate(-math.pi / 4, 0, 0), [2])
    return q


def depth_ceiling(layers):
    return 2 * sum(7 if layer['kind'] == 'ccx' else 1 for layer in layers if layer['gates']) + 1


def assemble(layers, mask, constant=0):
    validate(layers)
    assert 0 <= mask < 1 << 18 and constant in (0, 1)
    e = QuantumCircuit(18)
    primitive = margolus()
    for layer in layers:
        for gate in layer['gates']:
            if layer['kind'] == 'x':
                e.append(U3Gate(math.pi, 0, math.pi), gate)
            elif layer['kind'] == 'cx':
                e.cx(*gate)
            else:
                e.compose(primitive, gate, inplace=True)
    q = e.copy()
    for i in range(18):
        if mask >> i & 1:
            q.append(U3Gate(0, 0, math.pi), [i])
    q.compose(e.inverse(), inplace=True)
    # The optional Boolean constant only changes the permitted shared global
    # phase; omit it physically. Literal inversion cancels every RCCX phase.
    assert set(q.count_ops()) <= {'u3', 'cx'}
    assert q.depth() <= depth_ceiling(layers)
    return q


def layout(nonlin, affine):
    """Spread CX layers before and between nonlinear layers; no useless tail.

    A final invertible linear layer cannot change the midpoint affine span.
    """
    layers = []
    for i in range(nonlin):
        for _ in range(affine // nonlin + int(i < affine % nonlin)):
            layers.append({'kind': 'cx', 'gates': []})
        layers.append({'kind': 'ccx', 'gates': []})
    return layers


def random_matching(kind, rng, density=0.5):
    order = rng.sample(range(18), 18)
    arity = {'x': 1, 'cx': 2, 'ccx': 3}[kind]
    return [order[i:i + arity] for i in range(0, 18, arity) if rng.random() < density]


def mutate(layers, rng):
    result = [{'kind': layer['kind'], 'gates': [list(g) for g in layer['gates']]} for layer in layers]
    i = rng.randrange(len(result))
    layer = result[i]
    gates = layer['gates']
    arity = {'x': 1, 'cx': 2, 'ccx': 3}[layer['kind']]
    choice = rng.random()
    if choice < 0.08:
        layer['gates'] = random_matching(layer['kind'], rng)
    elif choice < 0.22 and gates:
        gates.pop(rng.randrange(len(gates)))
    elif choice < 0.55 and gates:
        # Swapping physical labels across an entire matching retains disjointness.
        a, b = rng.sample(range(18), 2)
        layer['gates'] = [[b if w == a else a if w == b else w for w in g] for g in gates]
    elif choice < 0.73 and gates:
        rng.shuffle(gates[rng.randrange(len(gates))])
    elif choice < 0.94:
        free = sorted(set(range(18)) - {w for g in gates for w in g})
        if len(free) >= arity:
            gates.append(rng.sample(free, arity))
    else:
        # Move a whole layer within the schedule; both budgets remain fixed.
        result.insert(rng.randrange(len(result)), result.pop(i))
    return result


def save_exact(layers, fit, out):
    assert parity(semantic(layers), fit['mask'], fit['constant']) == TARGET
    q = assemble(layers, fit['mask'], fit['constant'])
    path = out / f'direct_d{q.depth()}_cx{q.count_ops().get("cx", 0)}.qasm'
    assert not path.exists()
    path.write_text(qasm2.dumps(q))
    from exhaustive_verify import exhaustive
    exhaustive(path)
    return str(path)


def structured_seed(nonlin, affine, operations):
    """Paid affine prefix followed by a greedy physical nonlinear network.

    Prefix operations are chronological physical gates. Initial cube choices
    score parity toggles by exact truth tables; nearest_affine then reoptimizes
    the full midpoint span. No uncharged transformed coordinates are used.
    """
    assert len(operations) <= affine
    layers = [{'kind': op[0], 'gates': [list(op[1:])]} for op in operations]
    layers += layout(nonlin, affine - len(operations))
    for li, layer in enumerate(layers):
        if layer['kind'] != 'ccx':
            continue
        used = set()
        while len(used) <= 15:
            wires = semantic(layers[:li + 1])
            fit = nearest_affine(wires)
            pred = parity(wires, fit['mask'], fit['constant'])
            free = sorted(set(range(18)) - used)
            best = fit['distance']
            selected = None
            for ai, a in enumerate(free):
                for b in free[ai + 1:]:
                    product = wires[a] & wires[b]
                    for t in free:
                        if t == a or t == b:
                            continue
                        after = pred ^ (product if fit['mask'] >> t & 1 else 0)
                        for toggle in (0, wires[t] ^ product):
                            distance = (after ^ toggle ^ TARGET).bit_count()
                            distance = min(distance, 4096 - distance)
                            if distance < best:
                                best, selected = distance, [a, b, t]
            if selected is None:
                break
            layer['gates'].append(selected)
            used.update(selected)
    return layers


def search(out, nonlin, affine, seconds, seed, preconditioner=None):
    assert not out.exists()
    out.mkdir(parents=True)
    rng = random.Random(seed)
    layers = (structured_seed(nonlin, affine, json.loads(preconditioner.read_text())['substitution_ops'])
              if preconditioner else layout(nonlin, affine))
    current = nearest_affine(semantic(layers))
    initial_fit = current.copy()
    best = dict(current, layers=layers)
    started = time.monotonic()
    iterations = 0
    improvements = []
    while time.monotonic() - started < seconds and best['distance']:
        proposed = mutate(layers, rng)
        fit = nearest_affine(semantic(proposed))
        # Periodic reheating permits neutral/worse interior changes. Fitness is
        # always the exact 4096-input distance, not a sampled success rate.
        temperature = 2 + 18 * (1 - (iterations % 1000) / 1000)
        delta = fit['distance'] - current['distance']
        if delta <= 0 or rng.random() < math.exp(-delta / temperature):
            layers, current = proposed, fit
        iterations += 1
        if fit['distance'] < best['distance']:
            best = dict(fit, layers=proposed)
            row = dict(iteration=iterations, seconds=time.monotonic() - started, **fit)
            improvements.append(row)
            (out / 'best.json').write_text(json.dumps(best, indent=2) + '\n')
            print(row, flush=True)
        if iterations % 2000 == 0:
            layers = best['layers']
            current = {k: best[k] for k in ('distance', 'mask', 'constant')}
    report = dict(nonlin=nonlin, affine=affine, preconditioner=str(preconditioner) if preconditioner else None,
                  conditional_depth_ceiling=2 * (7 * nonlin + affine) + 1,
                  seed=seed, initial_fit=initial_fit, seconds=time.monotonic() - started, iterations=iterations,
                  improvements=improvements, best=best, exact=best['distance'] == 0)
    if report['exact']:
        report['qasm'] = save_exact(best['layers'], best, out)
    (out / 'best.json').write_text(json.dumps(best, indent=2) + '\n')
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print({k: v for k, v in report.items() if k not in ('best', 'improvements')}, 'distance', best['distance'], flush=True)
    return report


def solve_layers(layers, free_layers, samples, target=TARGET, seconds=10):
    """Synthesize or repair arbitrary matching layers and a free phase mask.

    Fixed layers replay literally. Free layers include optional gates, permit
    arbitrary data targets, and have no special first-layer pairing. SAT on
    samples is provisional until all 4096 Boolean inputs pass replay.
    """
    validate(layers)
    assert samples and all(0 <= x < 4096 for x in samples)
    size = len(samples)
    s = z3.Solver()
    s.set(timeout=int(seconds * 1000))
    state = [z3.BitVecVal(sum(((x >> w) & 1) << i for i, x in enumerate(samples)), size) for w in range(12)]
    state += [z3.BitVecVal(0, size)] * 6
    definitions = {}
    def select(values, index):
        result = values[-1]
        for w in reversed(range(17)):
            result = z3.If(index == w, values[w], result)
        return result
    for li, layer in enumerate(layers):
        if li not in free_layers:
            for gate in layer['gates']:
                if layer['kind'] == 'x':
                    state[gate[0]] ^= z3.BitVecVal((1 << size) - 1, size)
                elif layer['kind'] == 'cx':
                    a, t = gate
                    state[t] = state[t] ^ state[a]
                else:
                    a, b, t = gate
                    state[t] = state[t] ^ (state[a] & state[b])
            continue
        arity = {'x': 1, 'cx': 2, 'ccx': 3}[layer['kind']]
        order = [z3.BitVec(f'p_{li}_{i}', 5) for i in range(18)]
        enabled = [z3.Bool(f'on_{li}_{i}') for i in range(18 // arity)]
        s.add([*[z3.ULT(v, 18) for v in order], z3.Distinct(order)])
        # Sort only interchangeable gates, never assign fixed physical wires.
        for j in range(len(enabled) - 1):
            s.add(z3.ULT(order[arity * j + arity - 1], order[arity * (j + 1) + arity - 1]))
        if arity == 3:
            for j in range(6):
                s.add(z3.ULT(order[3 * j], order[3 * j + 1]))
        products = []
        for j in range(len(enabled)):
            value = (z3.BitVecVal((1 << size) - 1, size) if arity == 1 else select(state, order[arity * j]))
            if arity == 3:
                value &= select(state, order[arity * j + 1])
            products.append(value)
        new = []
        for w in range(18):
            value = state[w]
            for j, product in enumerate(products):
                value = z3.If(z3.And(enabled[j], order[arity * j + arity - 1] == w), state[w] ^ product, value)
            fresh = z3.BitVec(f's_{li}_{w}', size)
            s.add(fresh == value)
            new.append(fresh)
        state = new
        definitions[li] = (arity, order, enabled)
    mask = [z3.Bool(f'phase_{w}') for w in range(18)]
    constant = z3.Bool('phase_constant')
    output = z3.If(constant, z3.BitVecVal((1 << size) - 1, size), z3.BitVecVal(0, size))
    for w in range(18):
        output ^= z3.If(mask[w], state[w], z3.BitVecVal(0, size))
    wanted = sum(((target >> x) & 1) << i for i, x in enumerate(samples))
    s.add(output == z3.BitVecVal(wanted, size))
    started = time.monotonic()
    status = s.check()
    record = dict(status=str(status), solve_seconds=time.monotonic() - started, samples=size, free_layers=sorted(free_layers))
    if status != z3.sat:
        if status == z3.unknown:
            record['reason'] = s.reason_unknown()
        return record
    model = s.model()
    result = [{'kind': x['kind'], 'gates': [list(g) for g in x['gates']]} for x in layers]
    for li, (arity, order, enabled) in definitions.items():
        physical = [model.eval(v, model_completion=True).as_long() for v in order]
        result[li]['gates'] = [physical[arity * i:arity * (i + 1)] for i, on in enumerate(enabled) if z3.is_true(model.eval(on, model_completion=True))]
    phase_mask = sum(int(z3.is_true(model.eval(v, model_completion=True))) << w for w, v in enumerate(mask))
    phase_constant = int(z3.is_true(model.eval(constant, model_completion=True)))
    residual = parity(semantic(result), phase_mask, phase_constant) ^ target
    record.update(layers=result, mask=phase_mask, constant=phase_constant, distance=residual.bit_count(),
                  counterexamples=[x for x in range(4096) if residual >> x & 1])
    return record


def repair(out, checkpoint, seconds, rounds=3, free_count=2):
    assert not out.exists()
    out.mkdir(parents=True)
    best = json.loads(checkpoint.read_text())
    layers = best['layers']
    # Include the final nonlinear layer and its preceding layer initially.
    last_nonlin = max(i for i, layer in enumerate(layers) if layer['kind'] == 'ccx')
    free = set(range(max(0, last_nonlin - free_count + 1), last_nonlin + 1))
    wrong = parity(semantic(layers), best['mask'], best['constant']) ^ TARGET
    bad = [x for x in range(4096) if wrong >> x & 1]
    rng = random.Random(16185)
    samples = sorted({0, 4095, *rng.sample(range(4096), 30), *rng.sample(bad, min(32, len(bad)))})
    rows = []
    for iteration in range(rounds):
        record = solve_layers(layers, free, samples, seconds=seconds)
        rows.append(record)
        if record['status'] == 'sat':
            if record['distance'] == 0:
                record['qasm'] = save_exact(record['layers'], record, out)
            else:
                samples = sorted(set(samples) | set(rng.sample(record['counterexamples'], min(32, len(record['counterexamples'])))))
        (out / 'report.json').write_text(json.dumps(rows, indent=2) + '\n')
        print({k: v for k, v in record.items() if k not in ('layers', 'counterexamples')}, flush=True)
        if record['status'] != 'sat' or record['distance'] == 0:
            break
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--nonlin', type=int, default=7)
    p.add_argument('--affine', type=int, default=18)
    p.add_argument('--seconds', type=float, default=60)
    p.add_argument('--seed', type=int, default=16185)
    p.add_argument('--repair', type=Path)
    p.add_argument('--free-count', type=int, default=2)
    p.add_argument('--preconditioner', type=Path)
    a = p.parse_args()
    if a.repair:
        repair(a.outdir, a.repair, a.seconds, free_count=a.free_count)
    else:
        search(a.outdir, a.nonlin, a.affine, a.seconds, a.seed, a.preconditioner)
