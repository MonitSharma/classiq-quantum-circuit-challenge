"""Rank loaders by the ready time of a chosen code coordinate's wire."""
import pickle, sys, glob, os
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile, full_gates
from kgen import side_plan
side = sys.argv[1]; want = int(sys.argv[2])
TBL = {'y': {1: (31, 22), 2: (40, 30), 4: (25, 18), 8: (33, 24)},
       'x': {1: (27, 21), 2: (38, 30), 4: (30, 23), 12: (29, 23)}}
def vt(g):
    wt = [0]*9; lu = [False]*9; t = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, tt = x[1], x[2]; m = max(wt[c], wt[tt]) + 1; wt[c] = wt[tt] = m; lu[c] = lu[tt] = False; t[tt] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return t
D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
rows = []
for p in sorted(set(glob.glob('runs/po_%s*.txt' % side))):
    try:
        bd, seq = load_beam(p)
        if not seq: continue
        d, pen, g = sa4(D, seq, tag='cr', binary='./c/sa4')
        if pen != 0 or check_loader2(g, D['newcode'])['max_dev'] > 1e-9: continue
        e, _ = profile(g); fx, W, co, rdy = side_plan(g, e, D, 0)
        if len(rdy) < 4 or want not in co: continue
        t = vt(g)
        s = [(t[w] if t[w] >= 0 else 0) for w in W]
        tb = TBL[side]
        vals = [max(rdy[k]+rdy[k]+tb.get(co[k], (99, 99))[1], s[k]+rdy[k]+tb.get(co[k], (99, 99))[0]) for k in range(4)]
        rows.append((rdy[co.index(want)], max(vals), os.path.basename(p), W, rdy, co, [rdy[i]-s[i] for i in range(4)], vals))
    except Exception:
        continue
rows.sort()
print(len(rows), f'{side} loaders; sorted by ready of coord {want}')
for r, b, p, W, rdy, co, gaps, vals in rows[:8]:
    print(f'  coord{want}-rdy {r}  bound {b}  gaps {gaps}  {p}  W {W} rdy {rdy} coords {co} vals {vals}')
