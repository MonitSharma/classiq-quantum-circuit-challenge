"""Evaluate every candidate beam output in runs/ and rank by the T=117 necessary condition."""
import pickle, sys, glob, os
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile
from kgen import side_plan
TOUCH = {'y': {1: 31, 2: 40, 4: 25, 8: 33}, 'x': {1: 26, 2: 38, 4: 29, 12: 29}}
pats = sys.argv[1:]
out = {}
for side in ('y', 'x'):
    D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
    files = sorted(set(f for p in pats for f in glob.glob(p)))
    rows = []
    for p in files:
        try:
            bd, seq = load_beam(p)
            if len(seq) == 0: continue
            d, pen, g = sa4(D, seq, tag='rk', binary='./c/sa4')
            chk = check_loader2(g, D['newcode'])
            if pen != 0 or chk['max_dev'] > 1e-9: continue
            e, _ = profile(g)
            fx, W, co, rdy = side_plan(g, e, D, 0)
            if len(rdy) < 4: continue
            tc = TOUCH[side]
            vals = [2*r + tc.get(c, 99) for r, c in zip(rdy, co)]
            rows.append((max(vals), sum(1 for v in vals if v == max(vals)), max(rdy), sum(rdy), p, W, rdy, co, vals))
        except Exception:
            continue
    rows.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    print(f'===== {side}: {len(rows)} valid candidates')
    seen = set()
    n = 0
    for mx, cnt, mrd, sm, p, W, rdy, co, vals in rows:
        k = (tuple(sorted(W)), tuple(sorted(rdy)))
        if k in seen: continue
        seen.add(k); n += 1
        print(f'  max {mx} atmax {cnt} rdy_max {mrd} sum {sm} W {W} rdy {rdy} coords {co} vals {vals}  <- {os.path.basename(p)}')
        if n >= 10: break
