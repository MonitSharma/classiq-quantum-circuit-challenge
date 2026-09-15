"""Direct compute/Z/uncompute synthesis with ordered gate-selection variables.

Three differences from post190_direct_boolean_template:

* the first nonlinear layer takes an arbitrary perfect matching of the twelve
  coordinate wires instead of the hardcoded adjacent products;
* layers are encoded as ordered gate slots (control/target index variables with
  pairwise wire-disjointness) rather than an 18-element permutation per layer,
  which removes the 18! relabelling symmetry of the old encoding;
* counterexample sampling starts from representatives of the row/column class
  quotient instead of uniform random points.

Targets are unrestricted, so coordinate wires may be overwritten; correctness is
restored by the inverse half of the oracle. A timeout is UNKNOWN, never an
impossibility proof and never a circuit result.
"""
import argparse, json, random, time
from pathlib import Path
import numpy as np
import z3
from qiskit import QuantumCircuit, qasm2
from distributed_frame_search import native
from exhaustive_verify import exhaustive
from two_stage_oracle import logo

WIRES = 18
ANCILLAS = list(range(12, 18))
OUT = 17
ADJACENT = ((0, 1), (2, 3), (4, 5), (6, 7), (8, 9), (10, 11))
BEST_ANF = ((0, 6), (1, 2), (3, 7), (4, 11), (5, 10), (8, 9))     # covers 867/886
NEAR_ANF = ((0, 1), (2, 3), (4, 11), (5, 10), (6, 7), (8, 9))     # covers 865/886
MATCHINGS = dict(adjacent=ADJACENT, best=BEST_ANF, near=NEAR_ANF)


def ceiling(layers, gaps):
    return 2 * (9 * layers + gaps * (layers - 1)) + 1


def classes():
    """Row and column class representatives of the logo quotient."""
    rows, cols = {}, {}
    for y in range(64):
        rows.setdefault(tuple(logo(x, y) for x in range(64)), []).append(y)
    for x in range(64):
        cols.setdefault(tuple(logo(x, y) for y in range(64)), []).append(x)
    return list(rows.values()), list(cols.values())


def structural_samples(limit, seed=190):
    """One point per (row class, column class) pair, thinned to `limit`."""
    rng = random.Random(seed)
    rowc, colc = classes()
    pool = []
    for ys in rowc:
        for xs in colc:
            x, y = rng.choice(xs), rng.choice(ys)
            pool.append(x | (y << 6))
    rng.shuffle(pool)
    on = [v for v in pool if logo(v & 63, v >> 6)]
    off = [v for v in pool if not logo(v & 63, v >> 6)]
    half = limit // 2
    picked = on[:half] + off[:limit - half]
    return sorted(set(picked) | {0, 4095})


def _select(values, index):
    out = values[-1]
    for i in reversed(range(len(values) - 1)):
        out = z3.If(index == i, values[i], out)
    return out


def _slots(solver, name, arity, count, ordered=True):
    """Ordered, wire-disjoint gate slots; `on` is monotone so unused slots trail."""
    idx = [[z3.BitVec(f'{name}_{i}_{j}', 5) for j in range(arity)] for i in range(count)]
    on = [z3.Bool(f'{name}_on_{i}') for i in range(count)]
    for i in range(count):
        for j in range(arity):
            solver.add(z3.ULT(idx[i][j], WIRES))
        solver.add(z3.Distinct(idx[i]))
        if arity == 3:
            solver.add(z3.ULT(idx[i][0], idx[i][1]))        # products commute
        if i:
            solver.add(z3.Implies(on[i], on[i - 1]))        # trailing inactive slots
            if ordered:
                solver.add(z3.Implies(on[i], z3.ULT(idx[i - 1][arity - 1], idx[i][arity - 1])))
    for i in range(count):
        for k in range(i + 1, count):
            for u in idx[i]:
                for v in idx[k]:
                    solver.add(z3.Implies(z3.And(on[i], on[k]), u != v))
    return idx, on


def _apply(state, idx, on, arity):
    out = []
    val = [(_select(state, g[0]) & _select(state, g[1])) if arity == 3
           else _select(state, g[0]) for g in idx]
    for w in range(WIRES):
        acc = state[w]
        for i, g in enumerate(idx):
            acc = acc ^ z3.If(z3.And(on[i], g[arity - 1] == w), val[i], z3.BitVecVal(0, state[0].size()))
        out.append(acc)
    return out


def solve(samples, layers, gaps, seconds, matching=ADJACENT):
    size = len(samples)
    solver = z3.Solver(); solver.set(timeout=int(seconds * 1000))
    state = [z3.BitVecVal(sum(((v >> w) & 1) << i for i, v in enumerate(samples)), size)
             for w in range(12)] + [z3.BitVecVal(0, size)] * 6
    target = z3.BitVecVal(sum(int(logo(v & 63, v >> 6)) << i for i, v in enumerate(samples)), size)
    plan = []
    for layer in range(layers):
        if layer:
            for gap in range(gaps):
                idx, on = _slots(solver, f'cx{layer}_{gap}', 2, 9)
                state = _apply(state, idx, on, 2); plan.append(('cx', idx, on))
        if layer == 0:
            new = state.copy()
            for i, (a, b) in enumerate(matching):
                new[ANCILLAS[i]] = state[ANCILLAS[i]] ^ (state[a] & state[b])
            state = new
            plan.append(('fixed', [(a, b, ANCILLAS[i]) for i, (a, b) in enumerate(matching)], None))
        else:
            idx, on = _slots(solver, f'and{layer}', 3, 6)
            state = _apply(state, idx, on, 3); plan.append(('and', idx, on))
    solver.add(state[OUT] == target)
    start = time.time(); status = solver.check()
    rec = dict(status=str(status), seconds=round(time.time() - start, 2), samples=size)
    if status != z3.sat:
        if status == z3.unknown:
            rec['reason'] = solver.reason_unknown()
        return rec, None
    m = solver.model(); ops = []
    for kind, idx, on in plan:
        if kind == 'fixed':
            ops.extend([('ccx', list(t)) for t in idx]); continue
        for i, flag in enumerate(on):
            if z3.is_true(m.eval(flag, model_completion=True)):
                ops.append(('ccx' if kind == 'and' else 'cx',
                            [m.eval(v, model_completion=True).as_long() for v in idx[i]]))
    rec['gates'] = len(ops)
    return rec, ops


def evaluate(ops):
    """Exact 4096-point evaluation of the forward network's output wire."""
    words = np.arange(4096, dtype=np.int64)
    for kind, w in ops:
        if kind == 'cx':
            words ^= (words >> w[0] & 1) << w[1]
        else:
            words ^= ((words >> w[0] & 1) & (words >> w[1] & 1)) << w[2]
    want = np.array([int(logo(v & 63, v >> 6)) for v in range(4096)])
    return np.flatnonzero((words >> OUT & 1) != want).tolist()


def assemble(ops):
    primitive = QuantumCircuit(3); primitive.rccx(0, 1, 2); primitive = native(primitive)
    assert primitive.depth() <= 9
    e = QuantumCircuit(WIRES)
    for kind, w in ops:
        if kind == 'cx': e.cx(*w)
        else: e.compose(primitive, w, inplace=True)
    q = e.copy(); q.u(0, 0, np.pi, OUT); q.compose(e.inverse(), inplace=True)
    from qiskit.circuit.library import U3Gate
    explicit = QuantumCircuit(WIRES); explicit.global_phase = q.global_phase
    for inst in q.data:
        wires = [q.find_bit(w).index for w in inst.qubits]
        explicit.append(U3Gate(*inst.operation.params) if inst.operation.name == 'u'
                        else inst.operation, wires)
    return min([explicit, native(explicit)], key=lambda c: (c.depth(), c.count_ops().get('cx', 0)))


def run(out, layers, gaps, seconds, rounds, matching, start_samples):
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(190)
    samples = structural_samples(start_samples)
    rows = []
    for it in range(rounds):
        rec, ops = solve(samples, layers, gaps, seconds, MATCHINGS[matching])
        rec['iteration'] = it; rows.append(rec)
        if ops is not None:
            bad = evaluate(ops); rec['counterexamples'] = len(bad)
            if not bad:
                q = assemble(ops)
                assert q.depth() <= ceiling(layers, gaps)
                f = out / f'direct_L{layers}g{gaps}_d{q.depth()}.qasm'
                f.write_text(qasm2.dumps(q)); exhaustive(f); rec['qasm'] = str(f)
            else:
                samples = sorted(set(samples) | set(rng.sample(bad, min(16, len(bad)))))
        (out / f'report_L{layers}g{gaps}_{matching}.json').write_text(json.dumps(
            dict(layers=layers, gaps=gaps, matching=matching,
                 native_depth_ceiling=ceiling(layers, gaps), rows=rows), indent=2))
        print({k: v for k, v in rec.items() if k != 'gates'} | {'gates': rec.get('gates')}, flush=True)
        if ops is None or not rec.get('counterexamples', 0):
            break
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--layers', type=int, default=5)
    p.add_argument('--gaps', type=int, default=3)
    p.add_argument('--seconds', type=float, default=60)
    p.add_argument('--rounds', type=int, default=4)
    p.add_argument('--matching', choices=sorted(MATCHINGS), default='best')
    p.add_argument('--samples', type=int, default=24)
    a = p.parse_args()
    run(a.outdir, a.layers, a.gaps, a.seconds, a.rounds, a.matching, a.samples)
