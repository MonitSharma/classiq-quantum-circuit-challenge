"""Correct timing (profile model: consecutive 1q on a wire merge). Per-wire last touch vs
last CX-target = the time after which the wire's VALUE is fixed."""
import pickle, sys
sys.path.insert(0, '.')
from kdrv import full_gates, profile
from sim import symbolic_final
R = '../../artifacts/118/recipes/'
for nm, f in (('x champ', 'x_loader_d44'), ('y champ', 'y_loader_d46_blkw'),
              ('x new', None), ('y new', None)):
    if f is None: continue
    D = pickle.load(open(R + f + '.pkl', 'rb'))
    g = full_gates(D)
    wt = [0]*9; lu = [False]*9; tgt = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, t = x[1], x[2]
            m = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m; lu[c] = lu[t] = False
            tgt[t] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    e, _ = profile(g)
    assert e == wt, (e, wt)
    rows = symbolic_final(g)
    sm = {}
    for b in range(1, 16):
        v = 0
        for k in range(4):
            if b >> k & 1: v ^= D['req'][k]
        sm[v] = b
    print(f'--- {nm}: {f}')
    for w in range(9):
        if rows[w] in sm:
            print(f'   w{w} code {sm[rows[w]]:2d}: rdy(last touch) {e[w]:3d}   value-fixed(last CX target) {tgt[w]:3d}   GAP {e[w]-tgt[w]}')
