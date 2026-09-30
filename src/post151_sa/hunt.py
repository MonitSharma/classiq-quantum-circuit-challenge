"""Find x loaders whose latest-ready wire carries the light px direction (code 1),
or whose ready max is <= 43.  Also rank all y loaders by ready max then sum."""
import pickle, sys, glob, os
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile
from kgen import side_plan
mode = sys.argv[1]
files = sorted(set(f for p in sys.argv[2:] for f in glob.glob(p)))
D = pickle.load(open(f'runs/s118{mode}.pkl', 'rb'))
rows = []
for p in files:
    try:
        bd, seq = load_beam(p)
        if not seq: continue
        d, pen, g = sa4(D, seq, tag='h', binary='./c/sa4')
        chk = check_loader2(g, D['newcode'])
        if pen != 0 or chk['max_dev'] > 1e-9: continue
        e, _ = profile(g)
        fx, W, co, rdy = side_plan(g, e, D, 0)
        if len(rdy) < 4: continue
        rows.append((max(rdy), sum(rdy), os.path.basename(p), W, rdy, co, max(e)))
    except Exception:
        continue
rows.sort()
print(f'{mode}: {len(rows)} valid, showing all with ready_max<=45')
n = 0
for mx, sm, p, W, rdy, co, dep in rows:
    if mx > 45: continue
    latest = co[rdy.index(mx)]
    flag = '  <== px LAST' if latest == 1 else ''
    print(f'  max {mx} sum {sm} depth {dep} W {W} rdy {rdy} coords {co} latest-coord {latest}{flag}  {p}')
    n += 1
print('shown', n)
