"""Try an extra non-code workspace wire in the phase-kernel network."""
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ['CLASSIQ_ROOT'])
os.chdir(ROOT / 'src/post151_sa')
from kdrv import CO as OLD_CO, assemble
import kdrv
import kgen
from postopt import parse_ops, fuse
from canc import simplify
import smilp
from classiq_synth.core.verify import exhaustive_verify

OUT = ROOT / 'artifacts/phase_network117_20260922/helper9'
OUT.mkdir(exist_ok=True)
co = np.load(ROOT / 'artifacts/116/recipes/kernel_co.npy')
kdrv.CO = co
kdrv.KTERMS = list(map(int, np.flatnonzero(abs(co) > 1e-10)))
kgen.CO = co
kgen.KTERMS = kdrv.KTERMS
dx, dy, _ = __import__('pickle').load(open(ROOT / 'artifacts/116/recipes/loaders_plan.pkl', 'rb'))
plan = kgen.plan(dx, dy, helpers=1)
seq, wires, rows, ready, unload = plan
assert len(wires) == 9 and rows[-1] == 256

inputs = [str(len(kdrv.KTERMS)), ' '.join(map(str, kdrv.KTERMS))]
inputs += [f'{st} {r} {116-u}' for st, r, u in zip(rows, ready, unload)]
inp = '\n'.join(inputs) + '\n'
binary = './c/kbeam1289'
records = []
for target, width, seed in [(116, 4000, 2), (115, 16000, 2), (114, 16000, 3)]:
    inputs[-9:] = [f'{st} {r} {target-u}' for st, r, u in zip(rows, ready, unload)]
    inp = '\n'.join(inputs) + '\n'
    name = f'helper9_t{target}_w{width}_s{seed}'
    path = OUT / f'{name}.txt'
    env = dict(os.environ, SINGLES_PENDING='1', TOUCHBAD='1')
    started = time.monotonic()
    try:
        proc = subprocess.run([binary, str(width), '70', str(seed), '0.02',
                               str(path), '4', '0'], input=inp, text=True,
                              capture_output=True, env=env, timeout=240)
        (OUT / f'{name}.log').write_text(proc.stderr)
        record = dict(name=name, returncode=proc.returncode, seconds=time.monotonic()-started)
        if proc.returncode == 0:
            kernel, model_end, ncx = kgen.build_kg(plan, path)
            assembled = OUT / f'{name}_asm.qasm'
            record['assembled'] = assemble(dx, dy, kernel, str(assembled))
            record['cx_kernel'] = ncx
            record['exhaustive'] = exhaustive_verify(assembled)
            ops = fuse(simplify(fuse(parse_ops(assembled)), verbose=False))
            result = smilp.solve(ops, target, tlim=60, verbose=True)
            record[f'milp{target}'] = result is not None
            if result is not None:
                sched = OUT / f'{name}_m{target}.qasm'
                from postopt import write, depth
                write(fuse(result), sched)
                record['scheduled_depth'] = depth(fuse(result))
                record['scheduled_verification'] = exhaustive_verify(sched)
    except subprocess.TimeoutExpired:
        record = dict(name=name, status='TIMEOUT', seconds=time.monotonic()-started)
    records.append(record)
    (OUT / 'report.json').write_text(json.dumps(records, indent=2))
    print(record, flush=True)
    if record.get('scheduled_depth', 999) < 116:
        break
