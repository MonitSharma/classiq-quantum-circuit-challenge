# Schedule the seq conditional support with the freeze beam and report its ready vector.
import sys, os, pickle, subprocess, time
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile
from kgen import side_plan
D = pickle.load(open(sys.argv[1], 'rb'))
lb = sys.argv[2]
maxd = int(sys.argv[3]); W = int(sys.argv[4]); ns = int(sys.argv[5])
env = dict(os.environ)
env.update(dict(WFRZ='0', WFT='0.35', WFMAX='0.7', FZMAX='3', WREACH2='0.15', NP='18', WSPREAD='0.6', SPCAP='3'))
env['BLKWX'] = '1,1,1,100,1,1,1,1,1,1,1,1,60,1,1'
best = None
for seed in range(1, ns + 1):
    out = 'runs/sq_%d_%d.txt' % (maxd, seed)
    t0 = time.time()
    p = subprocess.run(['./c/lbeam4', str(W), '24', str(maxd), str(seed), '16', '0.5', out, '0.02'],
                       stdin=open(lb), capture_output=True, text=True, env=env)
    dt = time.time() - t0
    if p.returncode != 0:
        print('  fail s%d (%.0fs)' % (seed, dt), flush=True); continue
    bd, seq = load_beam(out)
    d, pen, g = sa4(D, seq, tag='sq', binary='./c/sa4')
    chk = check_loader2(g, D['newcode'])
    if pen != 0 or chk['max_dev'] > 1e-9:
        print('  s%d INVALID' % seed, flush=True); continue
    e, _ = profile(g); fx, Wl, co, rdy = side_plan(g, e, D, 0)
    print('OK s%d depth %d rdy %s coords %s W %s (%.0fs)' % (seed, max(e), rdy, co, Wl, dt), flush=True)
    key = (max(rdy), sum(rdy))
    if best is None or key < best[0]:
        best = (key, out, rdy, co, Wl)
if best:
    print('BEST', best[0], best[1], 'rdy', best[2], 'coords', best[3])
else:
    print('no solution at maxd', maxd)
