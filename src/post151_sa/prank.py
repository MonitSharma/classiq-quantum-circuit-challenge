# Rank parity-preserving loaders: verify control-only parity, report ready vector and coords.
import pickle, sys, glob
sys.path.insert(0, '.')
from kdrv import full_gates, profile
from kgen import side_plan
side = sys.argv[1]
PAR = 48 if side == 'x' else 32
D0 = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
for p in sorted(glob.glob(f'runs/parity_0923/protect_{side}_*.pkl')):
    try:
        D = pickle.load(open(p, 'rb'))
        g = full_gates(D)
        n = 9; d = [0]*n; rows = [1 << w for w in range(n)]; viol = 0
        for x in g:
            ws = [x[1], x[2]] if x[0][0] == 'cx' else [x[1]]
            l = max(d[q] for q in ws) + 1
            for q in ws: d[q] = l
            if x[0][0] == 'cx':
                c, t = x[1], x[2]
                if rows[t] == PAR: viol += 1
                rows[t] ^= rows[c]
        e, _ = profile(g); fx, W, co, rdy = side_plan(g, e, D, 0)
        print('%-42s depth %2d rdy %s coords %s viol %d' % (p.split('/')[-1], max(e), rdy, co, viol))
    except Exception as ex:
        print(p.split('/')[-1], 'ERR', ex)
