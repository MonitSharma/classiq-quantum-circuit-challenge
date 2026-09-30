"""Check bridge identities in the newly synthesized 116 kernel only."""
import json
import time
from pathlib import Path

from postopt import parse_ops, fuse, write
from rewrite117 import moves, optimized, score
from smilp import solve
from classiq_synth.core.verify import exhaustive_verify

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/phase_network117_20260922/bridge116'
OUT.mkdir(exist_ok=True)
ops = fuse(parse_ops(ROOT / 'artifacts/116/conditional_loader_116.qasm'))
times = [0] * 18
layers = []
for op in ops:
    layer = max(times[w] for w in op[1]) + 1
    layers.append(layer)
    for w in op[1]:
        times[w] = layer
code_wires = {7, 6, 11, 14, 1, 0, 2, 3}
selected = [m for m in moves(ops)
            if all(30 <= layers[i] <= 80 and set(ops[i][1]) <= code_wires for i in m[:2])]
records, best = [], []
started = time.monotonic()
print('selected bridges', len(selected), 'base', score(ops), flush=True)
for k, move in enumerate(selected):
    candidate, sc = optimized(ops, move, 3)
    record = dict(index=k, move=move, score=sc,
                  cx=sum(op[0] == 'cx' for op in candidate))
    records.append(record)
    best.append((sc, k, candidate))
    best.sort(key=lambda entry: (entry[0], entry[1]))
    best = best[:6]
    if sc[0] < 116:
        path = OUT / f'improved_{k}.qasm'
        write(candidate, path)
        record['verification'] = exhaustive_verify(path)
    if k % 20 == 0:
        print(k, 'best', best[0][:2], flush=True)
for sc, k, candidate in best:
    result = solve(candidate, 115, tlim=15, verbose=True)
    records[k]['milp_found_115'] = result is not None
    if result is not None:
        path = OUT / f'milp_{k}.qasm'
        write(fuse(result), path)
        records[k]['verification'] = exhaustive_verify(path)
(OUT / 'report.json').write_text(json.dumps(dict(seconds=time.monotonic()-started,
                                               records=records), indent=2))
print('DONE', len(selected), best[0][:2], flush=True)
