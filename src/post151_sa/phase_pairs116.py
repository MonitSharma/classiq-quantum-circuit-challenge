"""Try the new 116 phase polynomial with a small portfolio of existing loaders."""
import json
import os
import pickle
import subprocess
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
os.environ['CLASSIQ_ROOT'] = str(ROOT)
os.environ['CLASS_CODES'] = str(ROOT / 'artifacts/185/class_codes.json')
os.chdir(ROOT / 'src/post151_sa')
import ev116
from kdrv import full_gates
from kgen import plan
from lbeval2 import load_beam, sa4
from sim import check_loader2
from classiq_synth.core.verify import exhaustive_verify

OUT = ROOT / 'artifacts/phase_network117_20260922/loader_pairs'
OUT.mkdir(exist_ok=True)
CO = np.load(ROOT / 'artifacts/116/recipes/kernel_co.npy')
ev116.CO = CO
ev116.KTERMS = list(map(int, np.flatnonzero(abs(CO) > 1e-10)))
champ_x, champ_y, _ = pickle.load(open(ROOT / 'artifacts/116/recipes/loaders_plan.pkl', 'rb'))


def loader(side, filename):
    if filename == 'champ':
        return champ_x if side == 'x' else champ_y
    base = 'x_loader_d44' if side == 'x' else 'y_loader_d46_blkw'
    original = pickle.load(open(ROOT / f'artifacts/118/recipes/{base}.pkl', 'rb'))
    _, seq = load_beam('runs/' + filename + '.txt')
    _, penalty, gates = sa4(original, seq, binary='./c/sa4', tag='phase116_' + filename)
    assert penalty == 0 and check_loader2(gates, original['newcode'])['max_dev'] < 1e-9
    return dict(original, gates=gates, fix=[])


def stable(d):
    times = [0] * 9
    oneq = [False] * 9
    target = [-1] * 9
    for g in full_gates(d):
        if g[0][0] == 'cx':
            c, t = g[1:]
            layer = max(times[c], times[t]) + 1
            times[c] = times[t] = layer
            oneq[c] = oneq[t] = False
            target[t] = layer
        else:
            w = g[1]
            if not oneq[w]:
                times[w] += 1
            oneq[w] = True
    return target


records = []
for xf, yf in [('champ', 'po_y45a_s17'), ('champ', 'po_y46_s8'),
               ('po_xE4_s2', 'champ'), ('champ', 'po_yF1_s17')]:
    dx, dy = loader('x', xf), loader('y', yf)
    pl = plan(dx, dy)
    _, wires, rows, ready, unload = pl
    sx, sy = stable(dx), stable(dy)
    early = [(sx[w] if w < 9 else sy[w - 9]) for w in wires]
    early = [s if s >= 0 else ready[k] for k, s in enumerate(early)]
    name = f'{xf}_{yf}_T115_W16000_s2'
    output = OUT / (name + '.txt')
    pickle.dump((dx, dy, pl), open(OUT / (name + '.pkl'), 'wb'))
    inp = '\n'.join([str(len(ev116.KTERMS)), ' '.join(map(str, ev116.KTERMS))] +
                    [f'{st} {r} {115-u}' for st, r, u in zip(rows, ready, unload)]) + '\n'
    env = dict(os.environ, SINGLES_PENDING='1', TOUCHBAD='1', SRDY=','.join(map(str, early)))
    started = time.monotonic()
    result = dict(name=name, ready=ready, early=early)
    try:
        proc = subprocess.run(['./c/kbeam_wirehash', '16000', '65', '2', '0.02',
                               str(output), '4', '0'], input=inp, text=True,
                              capture_output=True, env=env, timeout=150)
        (OUT / (name + '.log')).write_text(proc.stderr)
        result['returncode'] = proc.returncode
        if proc.returncode == 0:
            ev116.DX, ev116.DY, ev116.pl = dx, dy, pl
            result['evaluation'] = ev116.evaluate(str(output), early, 115, 115, 30)
            path = result['evaluation'].get('qasm', str(output).replace('.txt', '_asm.qasm'))
            result['verification'] = exhaustive_verify(path)
    except subprocess.TimeoutExpired:
        result['status'] = 'TIMEOUT'
    result['seconds'] = time.monotonic() - started
    records.append(result)
    (OUT / 'report.json').write_text(json.dumps(records, indent=2))
    print(result, flush=True)
    if result.get('verification', {}).get('depth', 999) < 116:
        break
