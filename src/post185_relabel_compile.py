"""Use temporary wire relabelings to explore native compiler tie-breaking.

All wire labels are restored before scoring/serialization. This does not
assume that the user input wires start clean or change the oracle contract.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

from qiskit import QuantumCircuit, qasm2, transpile
from distributed_frame_search import materialize_output_layout
from post185_depth_walk import profile


def relabel(q, permutation):
    assert sorted(permutation) == list(range(q.num_qubits))
    result = QuantumCircuit(q.num_qubits, global_phase=q.global_phase)
    for inst in q.data:
        result.append(inst.operation, [permutation[q.find_bit(w).index] for w in inst.qubits])
    return result


def compile_permuted(q, permutation, seed, inverse):
    raw = relabel(q.inverse() if inverse else q, permutation)
    compiled = transpile(raw, basis_gates=['u3','cx'], qubits_initially_zero=False,
                         optimization_level=3, seed_transpiler=seed)
    compiled = materialize_output_layout(compiled)
    result = relabel(compiled, [permutation.index(i) for i in range(q.num_qubits)])
    return result


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    q = qasm2.load(a.source)
    rng = random.Random(a.seed)
    pool, rows, seen = [], [], set()
    started = time.monotonic()
    for trial in range(a.trials):
        perm = list(range(q.num_qubits))
        rng.shuffle(perm)
        candidate = compile_permuted(q, perm, trial, bool(trial % 2))
        d, critical = profile(candidate)
        text = qasm2.dumps(candidate)
        sha = hashlib.sha256(text.encode()).hexdigest()
        rows.append(dict(trial=trial, permutation=perm, inverse=bool(trial%2), depth=d,
                         critical=len(critical), cx=candidate.count_ops().get('cx',0), sha256=sha))
        if sha not in seen:
            seen.add(sha)
            pool.append(((d,len(critical)),trial,text))
            pool.sort()
            pool = pool[:a.keep]
        if trial % 100 == 0:
            print('trial',trial,'best depth/critical',pool[0][0],flush=True)
    for score, trial, text in pool:
        path = a.outdir/f'candidate{trial}_d{score[0]}.qasm'
        path.write_text(text)
        rows[trial]['path'] = str(path)
    report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                  trials=a.trials, seconds=time.monotonic()-started,
                  objective='Depth, then critical gates; no CX penalty',
                  retained=[r for r in rows if 'path' in r], rows=rows)
    (a.outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('retained',[(score,trial) for score,trial,_ in pool],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=Path('artifacts/185/two_stage_185.qasm'))
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--trials',type=int,default=400)
    p.add_argument('--seed',type=int,default=1853)
    p.add_argument('--keep',type=int,default=8)
    run(p.parse_args())
