"""Replay a recorded distributed oracle without running a parameter search."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
import distributed_ucry as d
import distributed_frame_search as s
import level_oracle as l


def build(recipe, base_kernel=None, verify_components=False):
    k = s.kernel(recipe['y'], recipe['x'], base_kernel)
    circuit = QuantumCircuit(18)
    components = []
    for stage in range(3):
        for side, label, wires in [('u', 'y', l.YW+l.YA), ('v', 'x', l.XW+l.XA)]:
            item = recipe[label]
            settings = item['stages'][stage]
            tabs = [np.array(l.angle_table(l.code_of(item['triple'], l.LEVEL[side+str(p)])[1]))
                    for p in (1, 2)]
            angles = [tabs[0], tabs[1]-tabs[0], -tabs[1]][stage]
            raw = d.structured_ucry(angles, [6, 7, 8], list(range(6)), settings['seed'],
                                    sparse=settings['sparse'], open_walk=settings['open_walk'])
            component = s.native(raw)
            if verify_components:
                error = d.verify_component(component, angles)
                components.append(dict(side=side, stage=stage, error=error,
                                       depth=component.depth(), basis_inputs=512))
            circuit.compose(component, wires, inplace=True)
        if stage < 2:
            circuit.compose(k, inplace=True)
    return s.native(circuit), components


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--recipe', type=Path, required=True)
    p.add_argument('--kernel', type=Path)
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--verify-components', action='store_true')
    args = p.parse_args()
    assert not args.outdir.exists()
    recipe = json.loads(args.recipe.read_text())
    base = qasm2.load(args.kernel) if args.kernel else None
    q, components = build(recipe, base, args.verify_components)
    args.outdir.mkdir(parents=True)
    path = args.outdir/f'distributed_level_{q.depth()}.qasm'
    path.write_text(qasm2.dumps(q))
    report = dict(depth=q.depth(), cx=q.count_ops().get('cx', 0), width=q.num_qubits,
                  qasm=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  recipe=recipe, component_checks=components,
                  kernel_source=str(args.kernel) if args.kernel else 'factored_base_kernel',
                  kernel_sha256=hashlib.sha256(args.kernel.read_bytes()).hexdigest() if args.kernel else None,
                  status='Candidate; requires exhaustive_verify.py before promotion')
    (args.outdir/'recipe.json').write_text(json.dumps(recipe, indent=2)+'\n')
    (args.outdir/'build.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
