"""Trade phase count for easier parity structure using exact unreachable-code freedoms."""
import itertools
import json
import math
import os
import time
from pathlib import Path

import numpy as np
from kgenco import build_F, CH

ROOT = Path(os.environ['CLASSIQ_ROOT'])
OUT = ROOT / 'artifacts/phase_network117_20260922/wide'
OUT.mkdir(exist_ok=True)
_, known = build_F()
grid = known.reshape(16, 16)
moves = []
for side, valid in [('x', grid.any(1)), ('y', grid.any(0))]:
    missing = list(map(int, np.flatnonzero(~valid)))
    for size in range(1, len(missing) + 1):
        for subset in itertools.combinations(missing, size):
            for sg in itertools.product([-1, 1], repeat=size - 1):
                v = np.array([sum(sign * (-1)**((m & z).bit_count())
                                  for z, sign in zip(subset, (1,) + sg))
                              for m in range(16)])
                v //= math.gcd(*map(abs, v))
                for other in range(16):
                    vv = np.zeros(256, dtype=np.int16)
                    for m, value in enumerate(v):
                        vv[(m << 4 | other) if side == 'x' else (other << 4 | m)] = value
                    moves.append(vv)
M = np.array(moves, dtype=np.int16)
assert np.max(abs(CH[:, known].T @ M.T)) == 0
deltas = np.concatenate([amp * M for amp in [1, -1, 2, -2, 4, -4, 8, 16]])
rows = [2, 8, 1, 4, 32, 64, 192, 16]
coordinate = {}
for s in range(256):
    value = 0
    for k, row in enumerate(rows):
        if s >> k & 1:
            value ^= row
    coordinate[value] = s
bits = np.array([[(coordinate[m] >> k) & 1 for k in range(8)] for m in range(256)])
weights = np.array([.3, .5, .5, 2, .5, 2, 2, 2])
seed = np.rint(np.load(ROOT / 'artifacts/116/recipes/kernel_co.npy') / math.pi * 32).astype(np.int16)
np.save(OUT / 'co_0.npy', seed / 32 * math.pi)
pool = [seed]
for path in sorted((ROOT / 'artifacts/phase_network117_20260922/alternating').glob('co_*.npy')):
    pool.append(np.rint(np.load(path) / math.pi * 32).astype(np.int16))
seen = {a.tobytes() for a in pool}
rng = np.random.default_rng(230916)
started = time.monotonic()
for iteration in range(500):
    a = pool[iteration] if iteration < len(pool) else pool[int(rng.integers(len(pool)))]
    trials = (a + deltas + 16) % 32 - 16
    trials[:, 0] = 0
    counts = np.count_nonzero(trials, axis=1)
    valid = np.flatnonzero(counts <= 72)
    physical = (trials[valid] != 0) @ bits
    cost = physical @ weights + .5 * counts[valid]
    selected = set(map(int, valid[np.argsort(cost)[:12]]))
    # Keep choices at each support size and random escapes, not only sparsest states.
    for count in range(63, 73):
        group = np.flatnonzero(counts[valid] == count)
        selected.update(map(int, valid[group[np.argsort(cost[group])[:2]]]))
    if len(valid):
        selected.update(map(int, rng.choice(valid, min(8, len(valid)), replace=False)))
    for j in sorted(selected):
        b = trials[j]
        key = b.tobytes()
        if key not in seen:
            seen.add(key)
            pool.append(b.copy())
    if iteration % 100 == 0:
        print('iteration', iteration, 'pool', len(pool), flush=True)
    if len(pool) > 12000:
        break

# Degree estimates whether phases have neighbours accessible by one physical-bit XOR.
# These are selection heuristics only; actual CX availability is enforced by the beam.
records = []
support_seen = set()
for i, a in enumerate(pool):
    support = a != 0
    count = int(support.sum())
    key = support.tobytes()
    if not 65 <= count <= 72 or key in support_seen:
        continue
    support_seen.add(key)
    phys = support @ bits
    degree = np.zeros(256, dtype=int)
    for row in rows:
        degree += support[np.arange(256) ^ row]
    isolated = int(np.count_nonzero(support & (degree == 0)))
    edges = int(degree[support].sum() // 2)
    records.append(dict(pool_index=i, terms=count, physical_counts=phys.tolist(),
                        isolated=isolated, edges=edges,
                        cost=float(phys @ weights + .5 * count)))
chosen = {}
for rank in [lambda r: r['cost'],
             lambda r: (r['isolated'], -r['edges'], r['cost']),
             lambda r: (r['physical_counts'][3], r['cost']),
             lambda r: (r['physical_counts'][5] + r['physical_counts'][6], r['cost'])]:
    for r in sorted(records, key=rank)[:12]:
        chosen[r['pool_index']] = r
for count in range(65, 73):
    for r in sorted((r for r in records if r['terms'] == count), key=lambda r: r['cost'])[:2]:
        chosen[r['pool_index']] = r
retained = []
for index, r in enumerate(chosen.values(), 1):
    a = pool[r['pool_index']]
    delta = (CH.T @ (a - seed) / 32)[known]
    delta -= delta[0]
    assert np.max(abs((delta + 1) % 2 - 1)) < 1e-10
    np.save(OUT / f'co_{index}.npy', a / 32 * math.pi)
    retained.append(dict(index=index, **r))
(OUT / 'report.json').write_text(json.dumps(dict(pool=len(pool), unique_supports=len(records),
                                               seconds=time.monotonic()-started,
                                               retained=retained), indent=2))
print('DONE', len(pool), 'supports', len(records), 'retained', len(retained), flush=True)
