"""Joint modular phase lifts for a three-output loader with free address phase.

H on three clean targets, D, H loads their Boolean code if D's phase, modulo
2*pi, is pi*(target dot code(address)) plus an address-only phase. That phase
is allowed only because the full oracle uses this exact encoder's inverse.
Unlike independent angle lifts, moves here may involve several target bits.
"""
import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator

from depth_parity_network import walsh
from distributed_frame_search import native
from post258_two_stage_anf import decode
import two_stage_oracle as ts

SCALE = 128


def values_for(side):
    codes = json.loads(Path('artifacts/188/class_codes.json').read_text())
    cls, mask, key = (ts.ROWCLS, 32, 'ylab') if side == 'y' else (ts.COLCLS, 48, 'xlab')
    lab = decode(codes[key])
    return np.array([lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)])


def starting_coefficients(values):
    phases = np.array([-.5 * sum(((int(values[w & 63]) >> b) & 1)
                                 * (-1) ** ((w >> (6+b)) & 1) for b in range(3))
                       for w in range(512)])
    co = SCALE * walsh(phases)
    assert np.max(abs(co - co.round())) < 1e-12
    co = co.round().astype(np.int16) % SCALE
    co[:64] = 0  # arbitrary address-only phase is harmless in E / K / inverse(E)
    return co


def lift_moves():
    # Adding 2*pi times a Boolean cube preserves every diagonal entry. Dropping
    # address-only Fourier terms afterward changes only the permitted gauge.
    rows, labels = [], []
    for cube in range(64, 512):
        degree = cube.bit_count()
        if degree > 8:
            continue
        for polarity in (0, cube):
            move = np.zeros(512, np.int16)
            for m in range(64, 512):
                if m & ~cube == 0:
                    move[m] = (256 >> degree) * (-1) ** ((m ^ (m & polarity)).bit_count())
            for mult in (1, -1, 2, -2, 4, -4, 8, 16, 32):
                v = (move * mult) % SCALE
                if v.any():
                    rows.append(v)
                    labels.append((cube, polarity, mult))
    moves, idx = np.unique(np.array(rows), axis=0, return_index=True)
    return moves, [labels[i] for i in idx]


def verify_phase(co, values):
    phases = walsh(np.asarray(co, float) / SCALE) * 512
    target = np.array([((w >> 6) & int(values[w & 63])).bit_count() % 2 for w in range(512)])
    residual = np.exp(1j * math.pi * (phases-target)).reshape(8, 64)
    error = float(np.max(abs(residual-residual[:1])))
    assert error < 1e-10, error
    return error


def search(side, seconds, seed):
    values = values_for(side)
    start = starting_coefficients(values)
    moves, _ = lift_moves()
    rng = np.random.default_rng(seed)
    current = start.copy()
    best = current.copy()
    best_count = int(np.count_nonzero(best))
    history = [dict(step=0, support=best_count, co=best.tolist())]
    begun = time.monotonic()
    step = 0
    while time.monotonic()-begun < seconds:
        step += 1
        candidates = (current[None, :] + moves) % SCALE
        counts = np.count_nonzero(candidates, axis=1)
        minimum = counts.min()
        chosen = int(rng.choice(np.flatnonzero(counts == minimum)))
        temperature = .1 + 2.5 * (1-(step % 250)/250)
        difference = int(np.count_nonzero(current))-int(minimum)
        if difference >= 0 or rng.random() < math.exp(max(-50, difference/temperature)):
            current = candidates[chosen]
        count = int(np.count_nonzero(current))
        if count < best_count:
            best, best_count = current.copy(), count
            err = verify_phase(best, values)
            row = dict(step=step, support=count, co=best.tolist(), phase_error=err)
            history.append(row)
            print('joint lift', side, step, count, flush=True)
        if step % 250 == 0:
            current = best.copy() if rng.random() < .7 else start.copy()
            for _ in range(2):
                current = (current + moves[int(rng.integers(len(moves)))]) % SCALE
    return dict(side=side, start_support=int(np.count_nonzero(start)), best_support=best_count,
                steps=step, moves=len(moves), seconds=time.monotonic()-begun,
                phase_error=verify_phase(best, values), history=history)


def compile_loader(co, values, seed=0):
    from post218_beam_phase import psynth
    co = np.asarray(co, float)
    co = (co + SCALE/2) % SCALE - SCALE/2
    targets = {m:float(co[m])*math.pi/SCALE for m in range(64, 512) if co[m] != 0}
    body = psynth(9, targets, seed=seed, beam=32, branch=12, alpha=6.,
                  timew=1., horizon=1.5, fill=2, guard=0)
    q = QuantumCircuit(9)
    q.h([6, 7, 8])
    q.compose(body, inplace=True)
    q.h([6, 7, 8])
    q = native(q)
    # Includes serialization; validate all promised input columns and phases.
    q = qasm2.loads(qasm2.dumps(q))
    op = Operator(q).data[:, :64]
    want = np.zeros_like(op)
    indices = np.arange(64) + 64 * values
    amps = op[indices, np.arange(64)]
    want[indices, np.arange(64)] = amps / abs(amps)
    error = float(np.max(abs(op-want)))
    assert error < 1e-10, error
    return q, error


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--outdir', type=Path, required=True)
    p.add_argument('--side', choices=['x','y'], required=True)
    p.add_argument('--seconds', type=float, default=45)
    p.add_argument('--compile', action='store_true')
    a = p.parse_args()
    assert not a.outdir.exists()
    a.outdir.mkdir(parents=True)
    report = search(a.side, a.seconds, 188 + (a.side == 'x'))
    (a.outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    if a.compile:
        q, err = compile_loader(report['history'][-1]['co'], values_for(a.side))
        path = a.outdir/f'loader_d{q.depth()}_cx{q.count_ops().get("cx",0)}.qasm'
        path.write_text(qasm2.dumps(q))
        report['native'] = dict(depth=q.depth(), cx=q.count_ops().get('cx',0),
                                error=err, path=str(path))
        (a.outdir/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print({k:v for k,v in report.items() if k!='history'}, flush=True)
