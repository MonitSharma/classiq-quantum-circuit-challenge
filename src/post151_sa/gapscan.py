"""Scan every candidate loader for its per-code-wire value-fixed gap (ready - last CX target).
The pull-in converts that gap into kernel slack, so large gaps are the new objective."""
import pickle, sys, glob, os
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile, full_gates
from kgen import side_plan
side = sys.argv[1]
files = sorted(set(f for p in sys.argv[2:] for f in glob.glob(p)))
D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))

def sgap(g):
    wt = [0]*9; lu = [False]*9; tgt = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, t = x[1], x[2]; m = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m; lu[c] = lu[t] = False; tgt[t] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return wt, tgt

rows = []
for p in files:
    try:
        bd, seq = load_beam(p)
        if not seq: continue
        d, pen, g = sa4(D, seq, tag='g', binary='./c/sa4')
        chk = check_loader2(g, D['newcode'])
        if pen != 0 or chk['max_dev'] > 1e-9: continue
        e, _ = profile(g)
        fx, W, co, rdy = side_plan(g, e, D, 0)
        if len(rdy) < 4: continue
        wt, tgt = sgap(full_gates({'gates': g, 'fix': []}))
        gaps = [e[w] - (tgt[w] if tgt[w] >= 0 else e[w]) for w in W]
        rows.append((min(gaps), max(rdy), sum(rdy), os.path.basename(p), W, rdy, co, gaps, max(e)))
    except Exception:
        continue
rows.sort(reverse=True)
print(f'{side}: {len(rows)} valid; best minimum-gap first')
for mg, mx, sm, p, W, rdy, co, gaps, dep in rows[:8]:
    print(f'  min-gap {mg:2d} max-rdy {mx} sum {sm} depth {dep} W {W} rdy {rdy} coords {co} gaps {gaps}  {p}')
