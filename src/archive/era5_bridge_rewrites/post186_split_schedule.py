"""Expose phases inside U3 gates before commuting, scheduling, and native fusion.

Every permutation preserves the expanded circuit's conservative dependency
graph. Splitting is verified gate-by-gate by phasepoly_input; final acceptance
uses the serialized complete oracle on all 4096 promised inputs.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import U3Gate
from distributed_frame_search import native
from post188_phasepoly_probe import phasepoly_input
from post190_commuting_schedule import dependency_graph, reordered, schedule


def split_native(q):
    source = qasm2.loads(phasepoly_input(q))
    out = QuantumCircuit(q.num_qubits)
    for inst in source.data:
        wires = [source.find_bit(w).index for w in inst.qubits]
        if inst.operation.name == 'cx':
            out.cx(*wires)
        elif inst.operation.name == 'h':
            out.append(U3Gate(math.pi/2, 0, math.pi), wires)
        else:
            assert inst.operation.name == 'rz'
            out.append(U3Gate(0, 0, float(inst.operation.params[0])), wires)
    return out


def run(a):
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    original = qasm2.load(a.source)
    q = split_native(original)
    expanded = a.outdir/'expanded.qasm'
    expanded.write_text(qasm2.dumps(q))
    ops, succ, pred = dependency_graph(q)
    started = time.monotonic()
    history = []
    best = (10**6, 10**6, 10**6)
    completed = 0
    for seed in range(a.trials):
        if completed and time.monotonic()-started >= a.seconds:
            break
        layers = schedule(ops, succ, pred, seed)
        candidate = native(reordered(q, layers, pred))
        score = (candidate.depth(), candidate.count_ops().get('cx', 0),
                 candidate.count_ops().get('u3', 0))
        completed += 1
        if score < best:
            best = score
            path = a.outdir/f'candidate{len(history)}_d{score[0]}_cx{score[1]}.qasm'
            path.write_text(qasm2.dumps(candidate))
            history.append(dict(seed=seed, depth=score[0], cx=score[1], u3=score[2],
                                expanded_depth=len(layers), path=str(path),
                                order=[i for layer in layers for i in layer]))
            print('best', seed, score, flush=True)
    report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
                  expanded=str(expanded), expanded_depth=q.depth(), trials=completed,
                  seconds=time.monotonic()-started, history=history)
    (a.outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    from exhaustive_verify import exhaustive
    exhaustive(Path(history[-1]['path']))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('artifacts/186/two_stage_186.qasm'))
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--trials', type=int, default=256)
    p.add_argument('--seconds', type=float, default=60)
    run(p.parse_args())
