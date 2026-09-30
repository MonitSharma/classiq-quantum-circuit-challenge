"""Search the new 116 polynomial with separate Z/control and X/target windows."""
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import ev116
from classiq_synth.core.verify import exhaustive_verify

ROOT = Path(os.environ['CLASSIQ_ROOT'])
OUT = ROOT / 'artifacts/phase_network117_20260922/typed116'
OUT.mkdir(exist_ok=True)
ev116.CO = np.load(ROOT / 'artifacts/116/recipes/kernel_co.npy')
ev116.KTERMS = list(map(int, np.flatnonzero(abs(ev116.CO) > 1e-10)))
_, _, rows, ready, unload = ev116.pl
records = []
for target, mu, wdl in [(115, .02, 0), (115, .08, .2)]:
    zs, xs, zd, xd = ev116.typed_windows(target)
    tag = f't{target}_mu{mu}_wdl{wdl}'
    path = OUT / (tag + '.txt')
    env = dict(os.environ, SINGLES_PENDING='1', TOUCHBAD='1', WDL=str(wdl))
    env.update({key: ','.join(map(str, value))
                for key, value in [('ZS', zs), ('XS', xs), ('ZD', zd), ('XD', xd)]})
    inp = '\n'.join([str(len(ev116.KTERMS)), ' '.join(map(str, ev116.KTERMS))] +
                    [f'{st} {r} {target-u}' for st, r, u in zip(rows, ready, unload)]) + '\n'
    record = dict(tag=tag, target=target, mu=mu, wdl=wdl, zs=zs, xs=xs, zd=zd, xd=xd)
    started = time.monotonic()
    try:
        proc = subprocess.run([str(ROOT / 'src/post151_sa/c/kbeam_wirehash'),
                               '16000', '65', '2', str(mu), str(path), '4', '0'],
                              input=inp, text=True, capture_output=True, env=env, timeout=150)
        (OUT / (tag + '.log')).write_text(proc.stderr)
        record['returncode'] = proc.returncode
        if proc.returncode == 0:
            kernel = ev116.build_kg_typed(ev116.pl, path, zs, zd)
            record['evaluation'] = ev116.evaluate_kg(kernel, str(OUT / tag), target, 30)
            qasm = record['evaluation'].get('qasm', str(OUT / tag) + '_asm.qasm')
            record['verification'] = exhaustive_verify(qasm)
    except subprocess.TimeoutExpired:
        record['status'] = 'TIMEOUT'
    record['seconds'] = time.monotonic() - started
    records.append(record)
    (OUT / 'report.json').write_text(json.dumps(records, indent=2))
    print(record, flush=True)
    if record.get('verification', {}).get('depth', 999) < 116:
        break
