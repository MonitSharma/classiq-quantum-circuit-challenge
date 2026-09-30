# Polish an existing x loader with sa4 (iters>0) under per-wire ready caps, aiming at the T=116 spec:
# Lx1's ready must come down without regressing the other three x wires.
import sys, os, pickle
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile, full_gates
from kgen import side_plan
D = pickle.load(open('runs/s118x.pkl', 'rb'))
src = sys.argv[1]
cap = int(sys.argv[2]) if len(sys.argv) > 2 else 43
iters = int(sys.argv[3]) if len(sys.argv) > 3 else 400000
bd, seq = load_beam(src)
d0, p0, g0 = sa4(D, seq, tag='pl0', binary='./c/sa4')
e0, _ = profile(g0); _, Wb, cob, rdyb = side_plan(g0, e0, D, 0)
lx1 = Wb[cob.index(4)]
print('base rdy', rdyb, 'coords', cob, 'W', Wb, 'Lx1 local wire', lx1, flush=True)
env = dict(os.environ)
env['DEPW'] = '0'
env['CAPS'] = ','.join(str(cap if w == lx1 else 60) for w in range(9))
env['SPANREQ'] = ','.join(map(str, D['req']))
os.environ.update(env)
d, pen, g = sa4(D, seq, tag='pl%d' % iters, iters=iters, binary='./c/sa4')
chk = check_loader2(g, D['newcode'])
print('polished depth', max(profile(g)[0]), 'pen', pen, 'dev', chk['max_dev'], flush=True)
if pen == 0 and chk['max_dev'] < 1e-9:
    e, _ = profile(g); fx, W, co, rdy = side_plan(g, e, D, 0)
    print('  rdy', rdy, 'coords', co, 'W', W, flush=True)
    D2 = dict(D); D2['gates'] = g; D2['fix'] = []; D2['depth'] = max(e)
    pickle.dump(D2, open('runs/polished_%d.pkl' % iters, 'wb'))
    print('  saved runs/polished_%d.pkl' % iters, flush=True)
else:
    print('  INVALID / no improvement')
