"""Integrate exact distributed-parity lookups into the two-comparison oracle."""
import argparse
import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2, transpile
import distributed_ucry as distributed
import level_oracle as level
from level_encoder_search_fast import CODES


def run(outdir, seeds, structured=False):
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    records = []
    for code_index, (yt, xt) in enumerate(CODES):
        if structured and code_index != 0:
            continue
        tabs = {}
        for name in ('u1', 'u2', 'v1', 'v2'):
            _, targets = level.code_of(yt if name[0] == 'u' else xt, level.LEVEL[name])
            tabs[name] = np.array(level.angle_table(targets))
        selected = {}
        for side in ('u', 'v'):
            tables = [tabs[side+'1'], tabs[side+'2']-tabs[side+'1'], -tabs[side+'2']]
            for stage, angles in enumerate(tables):
                best = None
                for seed in range(seeds):
                    generator = distributed.structured_ucry if structured else distributed.ucry
                    raw = generator(angles, [6, 7, 8], list(range(6)), seed)
                    q = transpile(raw, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                                  optimization_level=3, seed_transpiler=0)
                    score = q.depth(), q.count_ops().get('cx', 0)
                    if best is None or score < best[0]:
                        best = score, q, seed
                # Retain the existing dense implementation if it is cheaper.
                old18 = level.ucry(angles, [6, 7, 8], list(range(6)), 0)
                old = QuantumCircuit(9)
                for inst in old18.data:
                    old.append(inst.operation, [old18.find_bit(q).index for q in inst.qubits])
                old = transpile(old, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                                optimization_level=3, seed_transpiler=0)
                oldscore = old.depth(), old.count_ops().get('cx', 0)
                if oldscore < best[0]:
                    best = oldscore, old, 'dense'
                err = distributed.verify_component(best[1], angles)
                selected[side, stage] = best
                records.append(dict(code_index=code_index, side=side, stage=stage,
                                    depth=best[0][0], cx=best[0][1], seed=best[2], error=err))
                print(records[-1], flush=True)
        a, _ = level.code_of(yt, level.LEVEL['u1'])
        b, _ = level.code_of(xt, level.LEVEL['v1'])
        terms = level.kernel_terms(a, b)
        q = QuantumCircuit(18)
        for stage in range(3):
            for side, wires in [('u', level.YW+level.YA), ('v', level.XW+level.XA)]:
                q.compose(selected[side, stage][1], wires, inplace=True)
            if stage < 2:
                level.emit_kernel(q, terms, level.YA, level.XA)
        q = transpile(q, basis_gates=['u3', 'cx'], qubits_initially_zero=False,
                      optimization_level=3, seed_transpiler=0)
        path = outdir/f'code{code_index}_d{q.depth()}.qasm'
        path.write_text(qasm2.dumps(q))
        records.append(dict(oracle=True, code_index=code_index, depth=q.depth(),
                            cx=q.count_ops().get('cx', 0), path=str(path),
                            ytriple=yt, xtriple=xt))
        print(records[-1], flush=True)
        (outdir/'report.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--seeds', type=int, default=40)
    p.add_argument('--structured', action='store_true')
    args = p.parse_args()
    run(args.outdir, args.seeds, args.structured)
