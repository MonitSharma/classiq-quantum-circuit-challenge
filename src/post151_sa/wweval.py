# Evaluate specific loader beams: rdy, first-touch, window width, corrected per-wire bound.
import pickle, sys, glob
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile, full_gates
from kgen import side_plan
TBL = {'y': {1: (31, 22), 2: (40, 30), 4: (25, 18), 8: (33, 24)},
       'x': {1: (27, 21), 2: (38, 30), 4: (30, 23), 12: (29, 23)}}
def ww(g):
    d = [0]*9; first = [None]*9
    for x in g:
        w = [x[1], x[2]] if x[0][0] == 'cx' else [x[1]]
        l = max(d[q] for q in w) + 1
        for q in w:
            d[q] = l
            if first[q] is None: first[q] = l
    return max(d), first
side = sys.argv[1]
D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
for p in sys.argv[2:]:
    try:
        bd, seq = load_beam(p)
        if not seq: print(p, 'no seq'); continue
        d, pen, g = sa4(D, seq, tag='we', binary='./c/sa4')
        if pen != 0 or check_loader2(g, D['newcode'])['max_dev'] > 1e-9:
            print(p, 'INVALID'); continue
        e, _ = profile(g); fx, W, co, rdy = side_plan(g, e, D, 0)
        Dep, ft = ww(full_gates({'gates': g, 'fix': []}))
        widths = [(rdy[k] - (ft[W[k] if W[k] < 9 else W[k] - 9] or rdy[k])) for k in range(4)]
        vals = [widths[k] + TBL[side].get(co[k], (99, 99))[0] + Dep + 1 for k in range(4)]
        print('%-26s D %d rdy %s coords %s widths %s bound %d' % (p.split('/')[-1], Dep, rdy, co, widths, max(vals)))
    except Exception as ex:
        print(p, 'ERR', ex)
