"""Replay saved gate permutations and native fusions without a scheduling solver."""
import argparse
import hashlib
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2
from distributed_frame_search import native


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def build(package, outdir):
    assert not outdir.exists()
    recipe = json.loads((package / 'schedule_recipe.json').read_text())
    text = (package / recipe['source']).read_text()
    assert sha(text) == recipe['source_sha256']
    q = qasm2.loads(text)
    for stage in recipe['stages']:
        if 'order' in stage:
            assert sorted(stage['order']) == list(range(len(q.data)))
            out = QuantumCircuit(q.num_qubits, global_phase=q.global_phase)
            for i in stage['order']:
                inst = q.data[i]
                out.append(inst.operation, [q.find_bit(w).index for w in inst.qubits])
            q = out
        if stage.get('native'):
            q = native(q)
        text = qasm2.dumps(q)
        assert sha(text) == stage['sha256'], (sha(text), stage['sha256'])
        q = qasm2.loads(text)
    assert sha(text) == recipe['sha256']
    outdir.mkdir(parents=True)
    target = outdir / recipe['qasm']
    target.write_text(text)
    print('replayed', q.depth(), q.count_ops().get('cx', 0), sha(text), flush=True)
    return target


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--verify', action='store_true')
    a = p.parse_args()
    path = build(a.package, a.outdir)
    if a.verify:
        from exhaustive_verify import exhaustive
        exhaustive(path)
