"""Assemble the two-pass level oracle with AND-network encoders."""
import json
import sys
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile

import level_and_encoder as le
import level_oracle as lo

XW = list(range(6))          # x data wires
YW = list(range(6, 12))      # y data wires
ANC = list(range(12, 18))


def load_plan(path):
    d = json.loads(Path(path).read_text())
    return d, [(a, b) for a, b in d['ops']], d['targets']


def wires_for(side, anc_ids):
    base = YW if side == 'y' else XW
    return base + [ANC[i] for i in anc_ids]


def pick_slots(hist, targets, nregs):
    """Choose three registers to carry the code bits."""
    import itertools
    regs = list(le.VARS6) + [0] * (nregs - 6)
    for a, b, k in hist:
        regs[k] ^= a & b
    for combo in itertools.permutations(range(nregs), 3):
        ok = True
        trial = list(regs)
        for slot, tgt in zip(combo, targets):
            comb = le.small_decompose(tgt ^ trial[slot], trial)
            if comb is None or slot in comb:
                ok = False
                break
            for i in comb:
                if i != -1:
                    trial[slot] ^= trial[i]
                else:
                    trial[slot] ^= le.FULL
        if ok and all(trial[s] == t for s, t in zip(combo, targets)):
            return list(combo)
    return None


def build_pass(py, px, seed=0, tries=600):
    dy, ops_y, tg_y = py
    dx, ops_x, tg_x = px
    sides = le.allocate_joint(ops_y, tg_y, ops_x, tg_x, tries=tries, seed=seed)
    if sides is None:
        return None
    enc = QuantumCircuit(18)
    slots = []
    for side, s, tg in (('y', sides[0], tg_y), ('x', sides[1], tg_x)):
        nregs = len(s['regs'])
        sl = pick_slots(s['hist'], tg, nregs)
        if sl is None:
            return None
        w = wires_for(side, s['anc'])
        le.emit_network(enc, s['hist'], w, tg, sl, nregs)
        slots.append([w[i] for i in sl])
    alpha, _ = lo.code_of(tuple(dy['triple']), lo.LEVEL[dy['name']])
    beta, _ = lo.code_of(tuple(dx['triple']), lo.LEVEL[dx['name']])
    terms = lo.kernel_terms(alpha, beta)
    qc = QuantumCircuit(18)
    qc.compose(enc, inplace=True)
    lo.emit_kernel(qc, terms, slots[0], slots[1])
    qc.compose(enc.inverse(), inplace=True)
    return qc, terms, sides


def main(plandir, out, seeds=8):
    plans = {n: load_plan(Path(plandir) / f'plan_{n}.json') for n in ('u1', 'v1', 'u2', 'v2')}
    best = None
    for seed in range(seeds):
        qc = QuantumCircuit(18)
        ok = True
        info = []
        for yn, xn in (('u1', 'v1'), ('u2', 'v2')):
            r = build_pass(plans[yn], plans[xn], seed=seed)
            if r is None:
                ok = False
                break
            sub, terms, sides = r
            qc.compose(sub, inplace=True)
            info.append((len(sides[0]['hist']), len(sides[1]['hist']), len(terms)))
        if not ok:
            print('seed', seed, 'allocation failed', flush=True)
            continue
        t = transpile(qc, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                      optimization_level=3, seed_transpiler=seed)
        print('seed', seed, 'depth', t.depth(), dict(t.count_ops()), info, flush=True)
        if best is None or t.depth() < best[0]:
            best = (t.depth(), t)
    if best:
        Path(out).write_text(qasm2.dumps(best[1]))
        print('best depth', best[0], '->', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'artifacts/level_and.qasm')
