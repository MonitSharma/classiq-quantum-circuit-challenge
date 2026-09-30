"""Search real-valued unreachable-code phase freedoms, not only a fixed coefficient grid."""
import json
import math
import os
import time
from pathlib import Path

import numpy as np
from kgenco import build_F, CH, solve, check

ROOT = Path(os.environ['CLASSIQ_ROOT'])
OUT = ROOT / 'artifacts/phase_network117_20260922/continuous'
OUT.mkdir(exist_ok=True)
_, known = build_F()
records = []
started = time.monotonic()
best = 256
for seed in range(96):
    result = solve(np.random.default_rng(seed + 92023), rounds=12, jit=.8)
    if result is None:
        continue
    count, coefficients = result
    if check(coefficients) > 1e-9:
        continue
    support = tuple(map(int, np.flatnonzero(abs(coefficients) > 1e-9)))
    if len(support) < best:
        best = len(support)
        print('NEW SUPPORT', best, 'seed', seed, flush=True)
    if any(r['support'] == support for r in records):
        continue
    index = len(records)
    np.save(OUT / f'co_{index}.npy', coefficients * math.pi)
    records.append(dict(index=index, seed=seed, terms=len(support), support=list(support),
                        values=[float(coefficients[m]) for m in support],
                        check=float(check(coefficients))))
    (OUT / 'report.json').write_text(json.dumps(dict(best=best, records=records,
                                                     elapsed=time.monotonic()-started), indent=2))
    print('CANDIDATE', index, len(support), 'seed', seed, flush=True)
print('DONE', len(records), 'best', best, 'seconds', time.monotonic()-started, flush=True)
