# Corrected re-timing model.  The unload mirrors the loader, so the tail a wire still has to run after
# the kernel is the NUMBER OF LOADER GATES ON THAT WIRE (they are chained one per layer in the inverse),
# not the wire's ready time.  Recompute the compressible T with that tail.
import sys, collections, pickle
sys.path.insert(0, '.')
exec(open('try9.py').read().split("xs, xl, ys, yl, T =")[0])

DX = load_side('../../artifacts/118/recipes/x_loader_d44.pkl', 'champ', 'tx')
DY = load_side('../../artifacts/118/recipes/y_loader_d46_blkw.pkl', 'runs/po_yF1_s6.txt', 'ty')
sx = valuestable(DX); sy = valuestable(DY)
pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
svec = [((sx[w] if w < 9 else sy[w - 9]) if (sx[w] if w < 9 else sy[w - 9]) >= 0 else rdy[k]) for k, w in enumerate(W)]

gx = full_gates(DX); gy = full_gates(DY)
def opcount(local, side):
    g = gx if side == 'x' else gy
    return sum(1 for x in g if (x[1] if x[0][0] == 'cx' else x[1]) in (local,) or
               (x[0][0] == 'cx' and local in (x[1], x[2])))
TAIL = [opcount(W[k] if W[k] < 9 else W[k] - 9, 'x' if W[k] < 9 else 'y') for k in range(8)]
print('plan wire  side  rdy  loader-gate-count(=true unload tail)')
for k in range(8):
    print('  w%-3d     %s    %2d   %3d' % (W[k], 'x' if W[k] < 9 else 'y', rdy[k], TAIL[k]))

def model(kg, tail, verbose=False):
    body = kg[1:]
    pos = {w: [i for i, o in enumerate(body) if w in o[1:]] for w in W}
    rel = []
    for o in body:
        w = o[1]
        r = svec[W.index(w)] if o[0] == 'R' else rdy[W.index(w)]
        if o[0] == 'C': r = max(r, rdy[W.index(o[2])])
        rel.append(r)
    t = list(rel)
    for _ in range(6000):
        ch = False
        for w in W:
            ws = pos[w]
            for a, b in zip(ws, ws[1:]):
                if t[b] < t[a] + 1: t[b] = t[a] + 1; ch = True
        if not ch: break
    end = {w: max((t[i] for i in pos[w]), default=0) for w in W}
    vals = [end[W[k]] + tail[k] for k in range(8)]
    return t, end, vals, body, pos

kg = build_kg_s(pl, 'runs/p6_117_16000_2.txt', svec, 117)
t, end, vals, body, pos = model(kg, TAIL)
print('\nORIGINAL order: per-wire end+tail =', vals, '-> T =', max(vals))
t, end, vals, body, pos = model(kg, [rdy[k] for k in range(8)])
print('ORIGINAL order with the OLD (rdy) tail:', vals, '-> T =', max(vals))
