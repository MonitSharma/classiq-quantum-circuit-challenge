# Verify the control-only parity property on a BUILT loader: after a wire holds the parity row it is
# never a CX target again.  Also report the layer at which the parity row first appears (the Z-open time).
import pickle, sys
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import full_gates
from qa import parse, layers
side = sys.argv[1]
PAR = 48 if side == 'x' else 32
D = pickle.load(open(f'runs/s118{side}.pkl', 'rb'))
for p in sys.argv[2:]:
    bd, seq = load_beam(p)
    d, pen, g = sa4(D, seq, tag='pc', binary='./c/sa4')
    gg = list(full_gates({'gates': g, 'fix': []}))
    n = 9
    # layer each gate with the loader's own availability schedule, so "after" means later in time
    dl = [0]*n; rows = [1 << w for w in range(n)]; parw = None; ok = True; bad = []
    for x in gg:
        ws = [x[1], x[2]] if x[0][0] == 'cx' else [x[1]]
        l = max(dl[q] for q in ws) + 1
        for q in ws: dl[q] = l
        if x[0][0] == 'cx':
            c, t = x[1], x[2]
            if rows[t] == PAR:
                ok = False; bad.append(('target', l, t))
            rows[t] ^= rows[c]
        # a wire newly holding PAR becomes protected from the next layer on
    ts = [dl[w] for w in range(n) if rows[w] == PAR]
    print('%-24s valid %s  final parity wire(s) %s  parity-target violations %d  parity row first seen at layer %s'
          % (p.split('/')[-1], pen == 0 and check_loader2(g, D['newcode'])['max_dev'] < 1e-9,
             [w for w in range(n) if rows[w] == PAR], len(bad), min(ts) if ts else None))
    if bad[:3]: print('    first violations:', bad[:3])
