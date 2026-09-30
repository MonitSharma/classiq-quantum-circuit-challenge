"""Instant JOINT bound screen over all (x,y) loader pairs using per-coordinate touch/cx tables
measured from the verified 117 kernel.  Reports the best combinations."""
import pickle, sys, glob, os
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile, full_gates
from kgen import side_plan
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
def load_side(side):
    D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
    out = []
    for p in sorted(set(glob.glob(f'runs/po_{side}*.txt'))):
        try:
            bd, seq = load_beam(p)
            if not seq: continue
            d, pen, g = sa4(D, seq, tag='jt', binary='./c/sa4')
            if pen != 0 or check_loader2(g, D['newcode'])['max_dev'] > 1e-9: continue
            e, _ = profile(g); fx, W, co, rdy = side_plan(g, e, D, 0)
            if len(rdy) < 4: continue
            t = vt(g)
            s = [(t[w] if t[w] >= 0 else 0) for w in W]
            out.append((os.path.basename(p), rdy, co, s))
        except Exception:
            continue
    return out
ys = load_side('y'); xs = load_side('x')
print('y loaders', len(ys), ' x loaders', len(xs))
rows = []
for yn, yrdy, yco, ysv in ys:
    for xn, xrdy, xco, xsv in xs:
        vals = []
        for k in range(4):
            tc, cx = TBL['y'].get(yco[k], (99, 99))
            vals.append(max(yrdy[k]+yrdy[k]+cx, ysv[k]+yrdy[k]+tc))
        for k in range(4):
            tc, cx = TBL['x'].get(xco[k], (99, 99))
            vals.append(max(xrdy[k]+xrdy[k]+cx, xsv[k]+xrdy[k]+tc))
        rows.append((max(vals), xn, yn, yrdy, xrdy, min(vals)))
rows.sort()
print('--- best joint bounds ---')
seen = 0
for b, xn, yn, yrdy, xrdy, mn in rows:
    print(f'  bound {b}  {xn} + {yn}   yrdy {yrdy} xrdy {xrdy}')
    seen += 1
    if seen >= 12: break
