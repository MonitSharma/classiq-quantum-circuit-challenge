import pickle, sys, glob
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile
from kgen import side_plan
TOUCH = {'y': {1: 31, 2: 40, 4: 25, 8: 33}, 'x': {1: 26, 2: 38, 4: 29, 12: 29}}
side = sys.argv[1]
D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
res = []
for p in sorted(glob.glob(sys.argv[2])):
    try:
        bd, seq = load_beam(p)
        d, pen, g = sa4(D, seq, tag='ev', binary='./c/sa4')
        chk = check_loader2(g, D['newcode'])
        e, _ = profile(g)
        fx, W, co, rdy = side_plan(g, e, D[side] if False else D, 0)
        tc = TOUCH[side]
        prox = max(rr + tc.get(cc, 99) for rr, cc in zip(rdy, coords if False else co))
        ok = pen == 0 and chk['max_dev'] < 1e-9
        print(f'{p} pen {pen} depth {gate_depth(g)} rdy {rdy} coords {co} proxy {prox} valid {ok}', flush=True)
        if ok: res.append((prox, max(rdy), sum(rdy), p))
    except Exception as ex:
        print(p, 'ERR', repr(ex)[:100], flush=True)
res.sort()
for r in res[:5]: print('BEST', r)
