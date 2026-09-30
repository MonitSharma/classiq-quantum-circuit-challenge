"""Test the T=116 specification directly across the x population:
   Lx1 ready <= 43, or gap >= 4 at ready 44, or Lx1 touches <= 29 (table),
   WITHOUT regressing the other three x wires (their table bounds must stay <= 115)."""
import pickle, sys, glob, os
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile, full_gates
from kgen import side_plan
TBLX = {1: (27, 21), 2: (38, 30), 4: (30, 23), 12: (29, 23)}
def vt(g):
    wt = [0]*9; lu = [False]*9; t = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, tt = x[1], x[2]; m = max(wt[c], wt[tt]) + 1; wt[c] = wt[tt] = m; lu[c] = lu[tt] = False; t[tt] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return t
D = pickle.load(open('runs/s118x.pkl', 'rb'))
print('  file                    rdy                       gaps(Lx1 wire)  Lx1-r+t  other-max  VERDICT')
best = []
for p in sorted(set(glob.glob('runs/po_x*.txt'))):
    try:
        bd, seq = load_beam(p)
        if not seq: continue
        d, pen, g = sa4(D, seq, tag='sp', binary='./c/sa4')
        if pen != 0 or check_loader2(g, D['newcode'])['max_dev'] > 1e-9: continue
        e, _ = profile(g); fx, W, co, rdy = side_plan(g, e, D, 0)
        if len(rdy) < 4 or 4 not in co: continue
        t = vt(g)
        s = [(t[w] if t[w] >= 0 else 0) for w in W]
        i = co.index(4)
        gap = rdy[i] - s[i]; lx1 = s[i] + rdy[i] + TBLX[4][0]
        others = [max(rdy[k]+rdy[k]+TBLX.get(co[k], (99, 99))[1], s[k]+rdy[k]+TBLX.get(co[k], (99, 99))[0])
                  for k in range(4) if k != i]
        om = max(others)
        spec = (rdy[i] <= 43) or (rdy[i] == 44 and gap >= 4) or (TBLX[4][0] <= 29)
        verdict = 'MEETS SPEC' if (spec and om <= 115) else ('spec-part only' if spec else '')
        best.append((max(lx1, om), os.path.basename(p), rdy, gap, lx1, om))
        if spec:
            print(f'  {os.path.basename(p):24s} {rdy}  gap {gap}  {lx1}  other {om}  {verdict}')
    except Exception:
        continue
best.sort()
print('--- best overall by Lx1-bound ---')
for b, p, rdy, gap, lx1, om in best[:6]:
    print(f'  Lx1-bound {lx1} other {om} gap {gap} rdy {rdy}  {p}')
