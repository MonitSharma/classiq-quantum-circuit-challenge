"""Instant refined-bound screen over the whole loader population, using per-coordinate touch/cx
tables measured from the champion kernel (no beam run per candidate)."""
import pickle, sys, glob, os, collections
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile, full_gates
from kgen import side_plan

# per-coordinate (touches, cx) measured from the verified 117 kernel
TBL = {'y': {1: (31, 22), 2: (40, 30), 4: (25, 18), 8: (33, 24)},
       'x': {1: (27, 21), 2: (38, 30), 4: (27, 21), 12: (29, 23)}}

def valuestable(D):
    g = full_gates(D); wt = [0]*9; lu = [False]*9; tgt = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, t = x[1], x[2]; m = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m; lu[c] = lu[t] = False; tgt[t] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return tgt

side = sys.argv[1]
D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
files = sorted(set(f for p in sys.argv[2:] for f in glob.glob(p)))
rows = []
for p in files:
    try:
        bd, seq = load_beam(p)
        if not seq: continue
        d, pen, g = sa4(D, seq, tag='fb', binary='./c/sa4')
        chk = check_loader2(g, D['newcode'])
        if pen != 0 or chk['max_dev'] > 1e-9: continue
        e, _ = profile(g)
        fx, W, co, rdy = side_plan(g, e, D, 0)
        if len(rdy) < 4: continue
        tgt = valuestable({'gates': g, 'fix': []})
        s = [(tgt[w] if tgt[w] >= 0 else 0) for w in W]
        tb = TBL[side]
        vals = []
        for k in range(4):
            tc, cx = tb.get(co[k], (99, 99))
            vals.append(max(rdy[k] + rdy[k] + cx, s[k] + rdy[k] + tc))
        rows.append((max(vals), os.path.basename(p), W, rdy, co, s, vals))
    except Exception:
        continue
rows.sort()
print(f'{side}: {len(rows)} valid; best refined bound first')
for b, p, W, rdy, co, s, vals in rows[:10]:
    print(f'  bound {b}  {p}  W {W} rdy {rdy} coords {co} gaps {[rdy[i]-s[i] for i in range(4)]} vals {vals}')
