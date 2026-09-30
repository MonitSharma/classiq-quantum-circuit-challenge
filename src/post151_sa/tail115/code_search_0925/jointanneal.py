"""jointanneal.py iters seed [wk] : anneal x and y class labels for 2*max(loader proxy) + wk*kernel terms."""
import sys, json, math, random, numpy as np
sys.path.insert(0, '/work/k')
import labeval as E, kerneval as KE
iters = int(sys.argv[1]); seed = int(sys.argv[2]); WK = float(sys.argv[3]) if len(sys.argv) > 3 else 0.43
rnd = random.Random(seed); rng = np.random.default_rng(seed)
lab = {'x': dict(E.XL), 'y': dict(E.YL)}; K = {s: E.keys(s) for s in 'xy'}

def lproxy(side, l):
    r = E.frame_cost(side, l, rng, reps=1)
    b = min(r, key=lambda d: d['pre'] / 2.2 + d['L'] / 1.55 + 0.01 * d['total'])
    return b['pre'] / 2.2 + b['L'] / 1.55 + 0.01 * b['total'], b

cache = {}
def side_score(side, l):
    key = (side, tuple(sorted(l.items())))
    if key not in cache: cache[key] = lproxy(side, l)
    return cache[key]

def total(lx, ly):
    sx, bx = side_score('x', lx); sy, by = side_score('y', ly); kt = KE.kterms(lx, ly, reps=2)
    if kt is None: return 1e9, None
    return 2 * max(sx, sy) + WK * kt, dict(x=bx, y=by, kt=kt, sx=round(sx, 2), sy=round(sy, 2))

cs, info = total(lab['x'], lab['y']); best = (cs, {s: dict(lab[s]) for s in 'xy'}, info)
print('start', round(cs, 2), info, flush=True)
for it in range(iters):
    side = rnd.choice('xy'); new = dict(lab[side]); p = rnd.choice([0, 1]); grp = [k for k in K[side] if k[0] == p]
    if rnd.random() < 0.7:
        a, b = rnd.sample(grp, 2); new[a], new[b] = new[b], new[a]
    else:
        used = {new[k] for k in grp}; free = [l for l in range(8) if l not in used]
        if not free: continue
        a = rnd.choice(grp); new[a] = rnd.choice(free)
    trial = {**lab, side: new}
    s, inf = total(trial['x'], trial['y']); T = 2.0 * (1 - it / iters) + 0.1
    if s < cs or rnd.random() < math.exp((cs - s) / T):
        lab, cs = trial, s
        if s < best[0]:
            best = (s, {q: dict(lab[q]) for q in 'xy'}, inf); print('it', it, 'best', round(s, 2), inf, flush=True)
            json.dump({'score': s, 'info': inf, 'xlab': {f'{k[0]},{k[1]}': v for k, v in lab['x'].items()},
                       'ylab': {f'{k[0]},{k[1]}': v for k, v in lab['y'].items()}},
                      open(f'/work/k/joint_{seed}.json', 'w'))
print('done', best[0], best[2])
