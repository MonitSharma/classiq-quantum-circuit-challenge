"""Bounded native-depth parity-network search for the new factored kernel."""
import argparse
import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
from qiskit.quantum_info import Operator
from distributed_ucry import change_basis, walsh
from distributed_frame_search import factored_base_kernel


def run(outdir, beam_width, steps):
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    # Integer sum, not Boolean XOR: their phases agree modulo 2*pi, but the
    # integer lift has 13 phase parities instead of the Boolean table's 31.
    f = [(z & 1) * (((z >> 1 & 1) & (z >> 2 & 1)) +
                    ((z >> 3 & 1) & (z >> 4 & 1))) for z in range(32)]
    co = walsh([f])[0]
    angles = {m: float(-2*np.pi*co[m]) for m in range(1, 32) if abs(co[m]) > 1e-12}
    labels = {m: 1 << i for i, m in enumerate(angles)}
    complete = (1 << len(labels))-1
    identity = tuple(1 << i for i in range(5))
    initial_seen = sum(labels.get(m, 0) for m in identity)
    beam = [(identity, initial_seen, (1,)*5, ())]
    candidates = []
    for step in range(steps):
        states = {}
        for basis, seen, depths, ops in beam:
            for a in range(5):
                for b in range(5):
                    if a == b:
                        continue
                    new_basis = list(basis)
                    new_basis[b] ^= new_basis[a]
                    new_basis = tuple(new_basis)
                    parity = new_basis[b]
                    added = labels.get(parity, 0) & ~seen
                    new_seen = seen | added
                    new_depths = list(depths)
                    new_depths[a] = new_depths[b] = max(depths[a], depths[b])+1
                    if added:
                        new_depths[b] += 1
                    new_ops = ops+((a, b, parity if added else 0),)
                    record = new_basis, new_seen, tuple(new_depths), new_ops
                    key = new_basis, new_seen
                    if key not in states or max(new_depths) < max(states[key][2]):
                        states[key] = record
        ranked = sorted(states.values(), key=lambda r: (2*(complete ^ r[1]).bit_count()+max(r[2]),
                                                        (complete ^ r[1]).bit_count(), sum(r[2])))
        finished = [r for r in ranked if r[1] == complete]
        candidates.extend(finished[:20])
        beam = ranked[:beam_width]
        print(step+1, 'missing', (complete ^ beam[0][1]).bit_count(),
              'forward_depth', max(beam[0][2]), 'finished', len(finished), flush=True)
    reference = Operator(factored_base_kernel()).data
    best = None
    records = []
    for basis, _, _, ops in candidates:
        middle = QuantumCircuit(5)
        for i, m in enumerate(identity):
            if m in angles:
                middle.rz(angles[m], i)
        for a, b, parity in ops:
            middle.cx(a, b)
            if parity:
                middle.rz(angles[parity], b)
        middle.compose(change_basis(basis, identity), inplace=True)
        q = QuantumCircuit(6)
        q.cz(0, 5)
        q.cx(0, 5)
        q.compose(middle, [5, 1, 3, 2, 4], inplace=True)
        q.cx(0, 5)
        q = transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                      optimization_level=3, seed_transpiler=0)
        score = q.depth(), q.count_ops().get('cx', 0)
        if best is None or score < best:
            op = Operator(qasm2.loads(qasm2.dumps(q))).data
            overlap = np.vdot(reference, op)
            error = float(np.max(np.abs(op-overlap/abs(overlap)*reference)))
            assert error < 1e-10
            best = score
            path = outdir/f'kernel_d{score[0]}_cx{score[1]}.qasm'
            assert not path.exists()
            path.write_text(qasm2.dumps(q))
            records.append(dict(depth=score[0], cx=score[1], error=error, path=str(path)))
            print('best', records[-1], flush=True)
    (outdir/'report.json').write_text(json.dumps(dict(beam_width=beam_width, steps=steps,
                                                    records=records), indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--beam', type=int, default=500)
    p.add_argument('--steps', type=int, default=14)
    args = p.parse_args()
    run(args.outdir, args.beam, args.steps)
