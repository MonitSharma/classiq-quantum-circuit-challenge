"""Rebuild the beam-scheduled 196-depth oracle from the recorded 218 codes.

Only the kernel schedule changes relative to `artifacts/218`: the same class
codes, the same integer phase lift and the same relative-phase encoders are
used, but the eight-wire phase polynomial is scheduled by the beam search in
`post218_beam_phase` instead of the earlier one-layer greedy.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2

import two_stage_oracle as ts
from depth_parity_network import walsh
from distributed_frame_search import native
from post218_beam_phase import psynth
from post224_relative_lookup import relative
from post258_two_stage_anf import decode

KERNEL_WIRES = [11, 12, 13, 14, 4, 15, 16, 17]
BEAM = dict(seed=209, beam=64, branch=14, alpha=5.0, timew=0.35)


def kernel(recipe):
    phases = walsh(np.array(recipe['co'], float) / 32) * 256 * math.pi
    co = walsh(phases)
    targets = {m: float(co[m]) for m in range(1, 256) if abs(co[m]) > 1e-12}
    return native(psynth(8, targets, global_phase=float(co[0]), **BEAM)), phases


def encoders(codes, yseed, xseed):
    enc = QuantumCircuit(18)
    for side, cls, mask, key, seed, wires in [
            (0, ts.ROWCLS, 32, 'ylab', yseed, ts.YW + ts.YA),
            (1, ts.COLCLS, 48, 'xlab', xseed, ts.XW + ts.XA)]:
        lab = decode(codes[key])
        values = [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]
        table = np.array([[math.pi * (c >> b & 1) for c in values] for b in range(3)])
        e, _ = relative(table, seed)
        if side:
            e.cx(5, 4)
        enc.compose(e, wires, inplace=True)
    return enc


def build(outdir, yseed=99, xseed=155):
    outdir.mkdir(parents=True, exist_ok=True)
    base = Path('artifacts/218')
    codes = json.loads((base / 'class_codes.json').read_text())
    recipe = json.loads((base / 'kernel_recipe.json').read_text())
    kern, phases = kernel(recipe)

    from qiskit.quantum_info import Operator
    op = Operator(qasm2.loads(qasm2.dumps(kern))).data
    want = np.diag(np.exp(1j * phases))
    overlap = np.vdot(want, op)
    kernel_error = float(np.max(abs(op - overlap / abs(overlap) * want)))
    assert kernel_error < 1e-10, kernel_error

    enc = encoders(codes, yseed, xseed)
    q = native(enc.compose(kern, KERNEL_WIRES).compose(enc.inverse()))
    text = qasm2.dumps(q)
    path = outdir / 'two_stage_196.qasm'
    path.write_text(text)
    (outdir / 'kernel.qasm').write_text(qasm2.dumps(kern))
    manifest = dict(sha256=hashlib.sha256(text.encode()).hexdigest(),
                    kernel_sha256=hashlib.sha256(qasm2.dumps(kern).encode()).hexdigest(),
                    depth=q.depth(), cx=q.count_ops().get('cx', 0), width=q.num_qubits,
                    kernel_depth=kern.depth(), kernel_cx=kern.count_ops().get('cx', 0),
                    kernel_max_error=kernel_error, beam=BEAM,
                    encoder_seeds=dict(y=yseed, x=xseed))
    (outdir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2), flush=True)
    return path


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--verify', action='store_true')
    a = p.parse_args()
    out = build(a.outdir)
    if a.verify:
        from exhaustive_verify import exhaustive
        exhaustive(out)
