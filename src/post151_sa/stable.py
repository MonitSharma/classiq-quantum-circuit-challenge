"""For each loader: per-wire last touch vs last CX-target (row-stability time) vs last CX-control."""
import pickle, sys
sys.path.insert(0, '.')
from kdrv import full_gates, profile
from sim import symbolic_final
R = '../../artifacts/118/recipes/'
for nm, f in (('x champ', 'x_loader_d44'), ('y champ', 'y_loader_d46_blkw')):
    D = pickle.load(open(R + f + '.pkl', 'rb'))
    g = full_gates(D)
    wt = [0] * 9; tgt = [0] * 9; ctl = [0] * 9
    for x in g:
        if x[0][0] == 'cx':
            c, t = x[1], x[2]
            m = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m
            tgt[t] = m; ctl[c] = m
        else:
            wt[x[1]] += 1
    e, _ = profile(g)
    rows = symbolic_final(g)
    sm = {}
    for b in range(1, 16):
        v = 0
        for k in range(4):
            if b >> k & 1: v ^= D['req'][k]
        sm[v] = b
    print(f'--- {nm}: {f}')
    for w in range(9):
        tag = f'code {sm[rows[w]]}' if rows[w] in sm else '      '
        print(f'   w{w}: last-touch {e[w]:3d}  last-CX-tgt {tgt[w]:3d}  last-CX-ctl {ctl[w]:3d}  {tag}')
