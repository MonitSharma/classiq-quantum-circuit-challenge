"""Package an already verified QASM with a literal matching gate-level QMOD.

Model creation is local; this does not synthesize, authenticate, or submit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from qiskit import qasm2
from classiq import (qfunc, QArray, QBit, Output, allocate, H, U, CX,
                     Constraints, OptimizationParameter, create_model, write_qmod)


def package(source, kernel, recipe, outdir):
    assert not outdir.exists()
    report = json.loads(source.with_suffix('.exhaustive.json').read_text())
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    assert sha == report['sha256'] and report['basis_inputs_checked'] == 4096
    q = qasm2.load(source)
    assert set(q.count_ops()) <= {'u3', 'cx'} and q.num_qubits == 18
    instructions = []
    for inst in q.data:
        wires = [q.find_bit(bit).index for bit in inst.qubits]
        instructions.append((inst.operation.name, [float(x) for x in inst.operation.params], wires))

    @qfunc
    def distributed_logo_oracle(q: QArray[QBit, 18]):
        for name, params, wires in instructions:
            if name == 'cx':
                CX(q[wires[0]], q[wires[1]])
            else:
                U(params[0], params[1], params[2], 0.0, q[wires[0]])

    @qfunc
    def main(q: Output[QArray[QBit, 18]]):
        allocate(18, q)
        # Full-support synthesis harness, as in the original notebook.
        # These Hadamards are not part of the packaged standalone QASM.
        for i in range(12):
            H(q[i])
        distributed_logo_oracle(q)

    model = create_model(main, constraints=Constraints(max_width=18,
                         optimization_parameter=OptimizationParameter.DEPTH))
    outdir.mkdir(parents=True)
    name = f'distributed_level_{q.depth()}'
    path = outdir/f'{name}.qasm'
    shutil.copyfile(source, path)
    shutil.copyfile(kernel, outdir/'kernel.qasm')
    raw_recipe = json.loads(recipe.read_text())
    clean_recipe = {side: {key: raw_recipe[side][key] for key in ('frame', 'triple', 'stages')}
                    for side in ('y', 'x')}
    (outdir/'recipe.json').write_text(json.dumps(clean_recipe, indent=2)+'\n')
    write_qmod(model, name, directory=outdir, decimal_precision=17)
    qmod = outdir/f'{name}.qmod'
    description = ('// Distributed Walsh-parity lookup oracle. Coordinates q[0:12]; clean ancillas q[12:18].\n'
                   '// Three exact lookup stages, two factored phase kernels, and complete restoration.\n'
                   '// distributed_logo_oracle mirrors every standalone QASM gate. main adds only the synthesis harness.\n'
                   f'// Authoritative QASM SHA-256: {sha}\n')
    qmod.write_text(description+qmod.read_text())
    manifest = dict(qasm=path.name, qmod=qmod.name, depth=q.depth(),
                    cx=q.count_ops().get('cx', 0), width=18, sha256=sha,
                    kernel_sha256=hashlib.sha256(kernel.read_bytes()).hexdigest(),
                    status='QASM already verified at source; rerun exhaustive verification on packaged copy',
                    qmod_note='Gate-level matching oracle plus 12-Hadamard synthesis harness; not resynthesized or submitted')
    (outdir/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--kernel', type=Path, required=True)
    p.add_argument('--recipe', type=Path, required=True)
    p.add_argument('--outdir', type=Path, required=True)
    args = p.parse_args()
    package(args.source, args.kernel, args.recipe, args.outdir)
