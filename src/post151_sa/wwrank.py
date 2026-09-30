# Rank loaders by the corrected per-wire quantity:  (rdy - first) + touches + D + 1.
# That is the true form of  T >= rdy + touches + tail  with  tail = D - first + 1.
import pickle, sys, glob, os
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile, full_gates
from kgen import side_plan
TBL = {'y': {1: (31, 22), 2: (40, 30), 4: (25, 18), 8: (33, 24)},
       'x': {1: (27, 21), 2: (38, 30), 4: (30, 23), 12: (29, 23)}}

def ww(g):
    d = [0]*9; first = [None]*9; last = [0]*9
    for x in g:
        w = [x[1], x[2]] if x[0][0] == 'cx' else [x[1]]
        l = max(d[q] for q in w) + 1
        for q in w:
            d[q] = l
            if first[q] is None: first[q] = l
            last[q] = l
    return max(d), first, last

side = sys.argv[1]
D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
rows = []
for p in sorted(set(glob.glob(f'runs/po_{side}*.txt'))):
    try:
        bd, seq = load_beam(p)
        if not seq: continue
        d, pen, g = sa4(D, seq, tag='ww', binary='./c/sa4')
        if pen != 0 or check_loader2(g, D['newcode'])['max_dev'] > 1e-9: continue
        e, _ = profile(g); fx, W, co, rdy = side_plan(g, e, D, 0)
        if len(rdy) < 4: continue
        Dep, ft, lt = ww(full_gates({'gates': g, 'fix': []}))
        vals = []
        for k in range(4):
            lw = W[k] if W[k] < 9 else W[k] - 9
            r = rdy[k]; f = ft[lw] or r
            tc = TBL[side].get(co[k], (99, 99))[0]
            vals.append((r - f) + tc + Dep + 1)
        rows.append((max(vals), os.path.basename(p), rdy, co, Dep, [ (rdy[k] - (ft[W[k] if W[k]<9 else W[k]-9] or rdy[k])) for k in range(4)], vals))
    except Exception:
        continue
rows.sort()
print(f'{side}: {len(rows)} loaders ranked by the corrected bound')
for b, p, rdy, co, Dep, widths, vals in rows[:8]:
    print(f'  bound {b}  {p:22s} D {Dep} rdy {rdy} coords {co} widths {widths} vals {vals}')
