"""Move input-only kernel phases into existing loader parity rows."""
import json
import argparse
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import ev116
import kdrv
from kdrv import PHYS, full_gates
from build import loader_ops, inverse_ops, emit
from postopt import parse_ops, fuse, write, depth
from canc import simplify
import smilp
from classiq_synth.core.verify import exhaustive_verify

ROOT = Path(os.environ['CLASSIQ_ROOT'])
os.chdir(ROOT / 'src/post151_sa')
OUT = ROOT / 'artifacts/phase_network117_20260922/phase_pullin'
OUT.mkdir(exist_ok=True)
CO = np.load(ROOT / 'artifacts/116/recipes/kernel_co.npy')
ev116.CO = kdrv.CO = CO
ALL_TERMS = list(map(int, np.flatnonzero(abs(CO) > 1e-10)))
ev116.KTERMS = ALL_TERMS.copy()
DX, DY, PLAN = ev116.DX, ev116.DY, ev116.pl


def assemble_pulled(kernel, output, placements):
    """Apply removed phases at proved input parity rows in the forward loaders."""
    gx, gy = full_gates(DX), full_gates(DY)
    lx, ly = loader_ops(gx, kdrv.XW), loader_ops(gy, kdrv.YW)
    forward_x, forward_y = list(lx), list(ly)
    for side, gate_index, local_wire, mask in placements:
        wiremap = kdrv.XW if side == 'x' else kdrv.YW
        forward = forward_x if side == 'x' else forward_y
        gate_list = gx if side == 'x' else gy
        assert gate_list[gate_index][0][0] == 'cx'
        angle = 2 * CO[mask]
        forward.insert(gate_index + 1,
                       ('1q', wiremap[local_wire], np.diag([1, np.exp(1j*angle)])))
    lops = forward_x + forward_y
    kops, remap = [], {w: w for w in range(18)}
    for g in kernel:
        if g[0] == 'S':
            for w, u in enumerate(g[1]):
                remap[PHYS[u]] = PHYS[w]
        elif g[0] == 'C':
            kops.append(('cx', PHYS[g[1]], PHYS[g[2]]))
        else:
            kops.append(('1q', PHYS[g[1]], np.diag([1, np.exp(1j*g[2])])))
    inv = [('cx', remap[o[1]], remap[o[2]]) if o[0] == 'cx'
           else ('1q', remap[o[1]], o[2]) for o in inverse_ops(lx + ly)]
    Path(output).write_text(emit(lops + kops + inv))
    return Path(output)


# Both rows are exact input parities throughout the indicated loader prefix:
# y mask 1 is input bit y5 from the start; x mask 16 is x4 XOR x5 on x wire 3
# immediately after gate 217. A gate-by-gate symbolic audit is in report.json.
parser = argparse.ArgumentParser()
parser.add_argument('--masks', default='1,16')
parser.add_argument('--targets', default='115,116')
args = parser.parse_args()
available = {1: ('y', 0, 5, 1), 16: ('x', 217, 3, 16)}
moved = set(map(int, args.masks.split(',')))
placements = [available[m] for m in sorted(moved)]
assert moved.issubset(ALL_TERMS)
ev116.KTERMS = [m for m in ALL_TERMS if m not in moved]
terms = ev116.KTERMS

records = []
for target in map(int, args.targets.split(',')):
    width, seed = 16000, 2
    seq, wires, rows, ready, unload = PLAN
    name = f'pullin_m{"-".join(map(str, sorted(moved)))}_t{target}_w{width}_s{seed}'
    path = OUT / f'{name}.txt'
    data = '\n'.join([str(len(terms)), ' '.join(map(str, terms))] +
                     [f'{st} {r} {target-u}' for st, r, u in zip(rows, ready, unload)]) + '\n'
    env = dict(os.environ, SINGLES_PENDING='1', TOUCHBAD='1',
               SRDY='26,37,42,43,28,40,42,44')
    started = time.monotonic()
    proc = subprocess.run(['./c/kbeam_wirehash', str(width), '65', str(seed),
                           '0.02', str(path), '4', '0'], input=data, text=True,
                          capture_output=True, env=env, timeout=150)
    (OUT / f'{name}.log').write_text(proc.stderr)
    record = dict(name=name, terms=len(terms), removed=sorted(moved), returncode=proc.returncode,
                  seconds=time.monotonic()-started)
    if proc.returncode == 0:
        kg = ev116.build_kg_s(PLAN, path, env['SRDY'].split(','), target)
        assembled = assemble_pulled(kg, OUT / f'{name}_asm.qasm', placements)
        record['verification'] = exhaustive_verify(assembled)
        ops = fuse(simplify(fuse(parse_ops(assembled)), verbose=False))
        record['simplified_depth'] = depth(ops)
        schedule = smilp.solve(ops, target, tlim=45, verbose=True)
        record['milp_found'] = schedule is not None
        if schedule is not None:
            scheduled = OUT / f'{name}_m{target}.qasm'
            write(fuse(schedule), scheduled)
            record['scheduled_depth'] = depth(fuse(schedule))
            record['scheduled_verification'] = exhaustive_verify(scheduled)
    records.append(record)
    (OUT / 'report.json').write_text(json.dumps(records, indent=2))
    print(record, flush=True)
    if record.get('scheduled_depth', 999) < 116:
        break
