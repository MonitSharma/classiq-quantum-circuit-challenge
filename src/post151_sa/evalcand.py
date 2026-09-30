# Evaluate a beam output against its own support dict: ready vector, coords, gaps.
import sys, os, pickle
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile, full_gates
from kgen import side_plan
D = pickle.load(open(sys.argv[1], 'rb'))
bd, seq = load_beam(sys.argv[2])
d, pen, g = sa4(D, seq, tag='ev2', binary='./c/sa4')
chk = check_loader2(g, D['newcode'])
print('layers', bd, 'sa4 depth', d, 'pen', pen, 'dev', chk['max_dev'])
if pen != 0 or chk['max_dev'] > 1e-9:
    print('INVALID'); sys.exit(0)
def vt(g):
    wt = [0]*9; lu = [False]*9; t = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, tt = x[1], x[2]; m = max(wt[c], wt[tt]) + 1; wt[c] = wt[tt] = m; lu[c] = lu[tt] = False; t[tt] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return t
e, _ = profile(g); fx, W, co, rdy = side_plan(g, e, D, 0)
t = vt(full_gates({'gates': g, 'fix': []}))
print('depth', max(e), 'rdy', rdy, 'coords', co, 'W', W)
print('gaps', [(rdy[k] - (t[W[k]] if t[W[k]] >= 0 else 0)) for k in range(len(W))])
print('profile', e)
D2 = dict(D); D2['gates'] = g; D2['fix'] = []; D2['depth'] = max(e)
out = sys.argv[2].replace('.txt', '.pkl')
pickle.dump(D2, open(out, 'wb')); print('saved', out)
