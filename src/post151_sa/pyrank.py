"""Rank y loaders by the ready time of the py wire (coord 1) - the individually-hard wire."""
import pickle, sys, glob, os
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile, full_gates
from kgen import side_plan
TBL = {1: (31, 22), 2: (40, 30), 4: (25, 18), 8: (33, 24)}
def vt(D):
    g = full_gates(D); wt = [0]*9; lu = [False]*9; t = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, tt = x[1], x[2]; m = max(wt[c], wt[tt]) + 1; wt[c] = wt[tt] = m; lu[c] = lu[tt] = False; t[tt] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return t
D = pickle.load(open('runs/s118y.pkl', 'rb'))
rows = []
for p in sorted(set(glob.glob('runs/po_y*.txt'))):
    try:
        bd, seq = load_beam(p)
        if not seq: continue
        d, pen, g = sa4(D, seq, tag='pp', binary='./c/sa4')
        if pen != 0 or check_loader2(g, D['newcode'])['max_dev'] > 1e-9: continue
        e, _ = profile(g); fx, W, co, rdy = side_plan(g, e, D, 0)
        if len(rdy) < 4 or 1 not in co: continue
        t = vt({'gates': g, 'fix': []})
        s = [(t[w] if t[w] >= 0 else 0) for w in W]
        vals = [max(rdy[k]+rdy[k]+TBL.get(co[k], (99, 99))[1], s[k]+rdy[k]+TBL.get(co[k], (99, 99))[0]) for k in range(4)]
        rows.append((rdy[co.index(1)], max(vals), os.path.basename(p), W, rdy, co, [rdy[i]-s[i] for i in range(4)], vals))
    except Exception:
        continue
rows.sort()
print(len(rows), 'loaders; sorted by py(coord 1) ready')
for pyr, b, p, W, rdy, co, gaps, vals in rows[:10]:
    print('  py-rdy', pyr, 'bound', b, 'gaps', gaps, p, 'W', W, 'rdy', rdy, 'coords', co, 'vals', vals)
