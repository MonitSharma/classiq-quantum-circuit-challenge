"""Build plan for (x loader, y loader) pair; write kin files and a JSON with ST/RDY/UNL/svec for device runs."""
import pickle, sys, os, json
sys.path.insert(0, '.')
exec(open('try2.py').read().split("xf, yf, T =")[0])
from kdrv import full_gates, KTERMS
def valuestable(D):
    g = full_gates(D); wt = [0]*9; lu = [False]*9; tgt = [-1]*9
    for x in g:
        if x[0][0] == 'cx':
            c, t = x[1], x[2]; m = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m; lu[c] = lu[t] = False; tgt[t] = m
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
    return tgt
xf, yf, tag = sys.argv[1], sys.argv[2], sys.argv[3]
DX = rebuild('x_loader_d44', xf, 'tx'); DY = rebuild('y_loader_d46_blkw', yf, 'ty')
pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
sx = valuestable(DX); sy = valuestable(DY)
sv = [(sx[w] if w < 9 else sy[w-9]) for w in W]; sv = [s if s >= 0 else rdy[k] for k, s in enumerate(sv)]
print('seq', seq_, 'W', W, 'ST', ST, 'rdy', rdy, 'unl', unl, 'sv', sv)
pickle.dump((DX, DY, pl), open(f'pair_{tag}.pkl', 'wb'))
json.dump({'ST': ST, 'RDY': rdy, 'UNL': unl, 'SV': sv, 'W': W, 'seq': seq_}, open(f'pair_{tag}.json', 'w'))
