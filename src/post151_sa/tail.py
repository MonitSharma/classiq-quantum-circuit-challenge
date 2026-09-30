# The unload mirrors the loader, so the tail a wire must still run after its last kernel op is
# determined by the mirror of the loader's own schedule: tail_w = D - (first layer of w) + 1.
# Compute it, verify against the measured 117 champion, and re-derive the true per-wire bound
#   T >= rdy_w + touches_w + tail_w.
import sys, pickle
sys.path.insert(0, '.')
exec(open('try9.py').read().split("xs, xl, ys, yl, T =")[0])
from qa import parse, layers

DX = load_side('../../artifacts/118/recipes/x_loader_d44.pkl', 'champ', 'tx')
DY = load_side('../../artifacts/118/recipes/y_loader_d46_blkw.pkl', 'runs/po_yF1_s6.txt', 'ty')

def tails(D):
    g = full_gates(D)
    # layer each gate by the loader's own wire-availability schedule
    d = [0]*9; first = [None]*9; last = [0]*9
    for x in g:
        w = [x[1], x[2]] if x[0][0] == 'cx' else [x[1]]
        l = max(d[q] for q in w) + 1
        for q in w:
            d[q] = l
            if first[q] is None: first[q] = l
            last[q] = l
    Dd = max(d)
    return Dd, {w: (Dd - first[w] + 1 if first[w] is not None else 0) for w in range(9)}

Dx, tx = tails(DX); Dy, ty = tails(DY)
print('x loader depth', Dx, 'y loader depth', Dy)
print('x per-wire first-touch tails', [tx[w] for w in range(9)])
print('y per-wire first-touch tails', [ty[w] for w in range(9)])

sx = valuestable(DX); sy = valuestable(DY)
pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
svec = [((sx[w] if w < 9 else sy[w - 9]) if (sx[w] if w < 9 else sy[w - 9]) >= 0 else rdy[k]) for k, w in enumerate(W)]
kg = build_kg_s(pl, 'runs/p6_117_16000_2.txt', svec, 117)
import collections
rot = collections.Counter(); cxc = collections.Counter(); cxt = collections.Counter()
for g in kg[1:]:
    if g[0] == 'C': cxc[g[1]] += 1; cxt[g[2]] += 1
    else: rot[g[1]] += 1
TAIL = [tx[W[k]] if W[k] < 9 else ty[W[k] - 9] for k in range(8)]
print()
print('plan wire side rdy touches tail  rdy+touches+tail')
best = 0
for k in range(8):
    w = W[k]; tc = rot[w] + cxc[w] + cxt[w]
    v = rdy[k] + tc + TAIL[k]; best = max(best, v)
    print('  w%-3d    %s   %2d   %3d   %3d      %3d' % (w, 'x' if w < 9 else 'y', rdy[k], tc, TAIL[k], v))
print('CORRECTED BOUND for this pair =', best, ' (achieved depth 117)')
