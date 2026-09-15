"""Measure saved sparse class codes, then optimize their actual care-set kernel.

Old frontier scores used a single ANF completion. This probe keeps only native,
all-input-verified loaders and searches free unreachable-state kernel phases.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator
from distributed_ucry import structured_ucry
from distributed_frame_search import native
from post196_linear_loader_frames import relative_body
from post196_code_frontier import EVAL8, ORDER8
from post218_beam_phase import psynth
from post258_joint_encoder_schedule import touches
from depth_parity_network import walsh
import two_stage_oracle as ts


def loader(code, rho, seeds):
    values = np.array(code) >> 1
    table = np.array([[math.pi * (v >> b & 1) for v in values] for b in range(3)])
    raw_bit = (rho & -rho).bit_length()-1
    best = None
    for seed in range(seeds):
        for sparse, opened in [(False,True), (True,False)]:
            raw = structured_ucry(table, [6,7,8], list(range(6)), seed,
                                  sparse=sparse, open_walk=opened)
            q = relative_body(raw)
            for b in range(6):
                if b != raw_bit and rho >> b & 1:
                    q.cx(b, raw_bit)
            q = native(q)
            score = q.depth(), q.count_ops().get('cx',0)
            if best is None or score < best[0]:
                best = score, q, dict(seed=seed,sparse=sparse,opened=opened,raw_bit=raw_bit)
    score, q, meta = best
    q = qasm2.loads(qasm2.dumps(q))
    op = Operator(q).data[:, :64]
    indices = np.arange(64) + 64 * values
    for v in range(64):
        if (v >> raw_bit & 1) != (code[v] & 1):
            indices[v] ^= 1 << raw_bit
    amps = op[indices, np.arange(64)]
    want = np.zeros_like(op)
    want[indices, np.arange(64)] = amps / abs(amps)
    error = float(np.max(abs(op-want)))
    assert error < 1e-10
    meta.update(depth=score[0],cx=score[1],error=error)
    return q, meta


def phase_problem(ycode, xcode):
    want = {}
    for y in range(64):
        for x in range(64):
            w = ycode[y] | (xcode[x] << 4)
            value = int(ts.logo(x,y))
            assert want.setdefault(w, value) == value
    piv = {}
    for w, value in want.items():
        row, rhs = EVAL8[w], value
        while row:
            i = (row & -row).bit_length()-1
            if i in piv:
                a,b = piv[i]
                row ^= a
                rhs ^= b
            else:
                piv[i] = row,rhs
                break
        else:
            assert not rhs
    sol = 0
    for i in sorted(piv,reverse=True):
        row,rhs = piv[i]
        if ((row & sol).bit_count() & 1) ^ rhs:
            sol |= 1 << i
    counts = np.array([(EVAL8[w] & sol).bit_count() for w in range(256)],float)
    care = np.array(sorted(want))
    target = np.array([want[w] for w in care],float)
    assert np.array_equal(counts[care] % 2, target)
    h = np.array([[(-1)**((int(w)&m).bit_count()%2) for m in range(256)] for w in care],float)
    return care,target,counts,h


def kernel_coefficients(ycode, xcode, restarts=4):
    care, truth, counts, h = phase_problem(ycode,xcode)
    rng = np.random.default_rng(188)
    best = (np.count_nonzero(walsh(counts)[1:]), walsh(counts))
    matrix = np.c_[h,-h]
    for restart in range(restarts):
        target = truth if restart % 2 else counts[care]
        weights = np.exp(rng.normal(0,.7,256))
        for step in range(6):
            weights[0] = 0
            r = linprog(np.r_[weights,weights], A_eq=matrix,b_eq=target,
                        bounds=(0,None),method='highs')
            assert r.success
            co = r.x[:256]-r.x[256:]
            co[abs(co)<1e-9] = 0
            assert np.max(abs(h@co-target)) < 1e-8
            size = np.count_nonzero(co[1:])
            if size < best[0]:
                best = size,co.copy()
            weights = 1/(abs(co)+.03) * np.exp(rng.normal(0,.2,256))
    return best[1],care,truth,h


def run(outdir, seeds, integrate):
    assert not outdir.exists()
    outdir.mkdir(parents=True)
    sources = []
    for path in sorted(Path('artifacts/post196_balance_v2').glob('*.json')):
        r = json.loads(path.read_text())
        if max(r['per_side_floor']) < 77:
            sources.append((str(path),r))
    front = json.loads(Path('artifacts/post196_frontier_v1/frontier.json').read_text())
    for i in (0,1,2):
        sources.append((f'frontier[{i}]',front[i]))
    cache, rows = {}, []
    for idx,(source,r) in enumerate(sources):
        encs, meta = [], []
        for key, rho in [('ycode',32),('xcode',r.get('x_rho',16))]:
            ck = (tuple(r[key]),rho)
            if ck not in cache:
                cache[ck] = loader(r[key],rho,seeds)
            q,m = cache[ck]
            encs.append(q)
            meta.append(m)
        row = dict(source=source, y=meta[0],x=meta[1],ycode=r['ycode'],xcode=r['xcode'])
        print('loaders',idx,source,meta,flush=True)
        rows.append(row)
        (outdir/'report.json').write_text(json.dumps(rows,indent=2)+'\n')
        if not integrate:
            continue
        co,care,truth,h = kernel_coefficients(r['ycode'],r['xcode'])
        row['kernel_support'] = int(np.count_nonzero(co[1:]))
        row['kernel_co'] = co.tolist()
        print('kernel support',idx,row['kernel_support'],flush=True)
        enc = QuantumCircuit(18)
        enc.compose(encs[0],ts.YW+ts.YA,inplace=True)
        enc.compose(encs[1],ts.XW+ts.XA,inplace=True)
        kw = [6+meta[0]['raw_bit'],12,13,14,meta[1]['raw_bit'],15,16,17]
        best = None
        for seed in (0,1):
            kernel = native(psynth(8,{m:float(co[m])*math.pi for m in range(1,256) if abs(co[m])>1e-10},
                           global_phase=float(co[0])*math.pi,seed=seed,beam=24,branch=10,
                           alpha=6.,timew=1.2,horizon=1.5,fill=2))
            op = Operator(kernel).data[:,care]
            want = np.zeros_like(op)
            want[care,np.arange(len(care))] = np.exp(1j*math.pi*truth)
            phase = np.vdot(want,op)
            assert np.max(abs(op-phase/abs(phase)*want)) < 1e-8
            circuit = native(enc.compose(kernel,kw).compose(enc.inverse()))
            score = circuit.depth(),circuit.count_ops().get('cx',0)
            if best is None or score < best[0]:
                best = score,circuit,kernel,seed
        score,circuit,kernel,seed = best
        path = outdir/f'candidate{idx}_d{score[0]}_cx{score[1]}.qasm'
        path.write_text(qasm2.dumps(circuit))
        row['candidate'] = dict(depth=score[0],cx=score[1],seed=seed,path=str(path))
        (outdir/'report.json').write_text(json.dumps(rows,indent=2)+'\n')
        print('complete',row['candidate'],flush=True)
        from exhaustive_verify import exhaustive
        exhaustive(path)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--seeds',type=int,default=12)
    p.add_argument('--integrate',action='store_true')
    a=p.parse_args()
    run(a.outdir,a.seeds,a.integrate)
