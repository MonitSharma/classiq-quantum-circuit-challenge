# Compare the re-timing model against the ACTUAL assembled circuit, per wire.
import sys, pickle, collections
sys.path.insert(0, '.')
exec(open('try9.py').read().split("xs, xl, ys, yl, T =")[0])
from qa import parse, layers

DX = load_side('../../artifacts/118/recipes/x_loader_d44.pkl', 'champ', 'tx')
DY = load_side('../../artifacts/118/recipes/y_loader_d46_blkw.pkl', 'runs/po_yF1_s6.txt', 'ty')
sx = valuestable(DX); sy = valuestable(DY)
pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
svec = [((sx[w] if w < 9 else sy[w - 9]) if (sx[w] if w < 9 else sy[w - 9]) >= 0 else rdy[k]) for k, w in enumerate(W)]
kg = build_kg_s(pl, 'runs/p6_117_16000_2.txt', svec, 117)

# actual: assemble with the ORIGINAL order and read per-qubit last layer
D0, ncx = assemble(DX, DY, kg, 'runs/diag_orig.qasm')
n, gg = parse('runs/diag_orig.qasm'); D, L = layers(n, gg)
last = [0]*n
for g, l in zip(gg, L):
    for q in g[1]: last[q] = l
print('assembled depth', D, ' (champion is 117)')
print()
print('plan wire  phys  rdy  model: last-kernel-op + unload = T   |  actual last layer of that physical qubit')
# model times on the original order
body = kg[1:]
pos = {w: [i for i, o in enumerate(body) if w in o[1:]] for w in W}
rel = []
for o in body:
    w = o[1]
    r = svec[W.index(w)] if o[0] == 'R' else rdy[W.index(w)]
    if o[0] == 'C': r = max(r, rdy[W.index(o[2])])
    rel.append(r)
t = list(rel)
for _ in range(4000):
    ch = False
    for w in W:
        ws = pos[w]
        for a, b in zip(ws, ws[1:]):
            if t[b] < t[a] + 1: t[b] = t[a] + 1; ch = True
    if not ch: break
# where is the kernel in the emitted gate list?
nk = len(kg) - 1
print('kernel ops', nk, ' cx in circuit', ncx)
for k, w in enumerate(W):
    e = max((t[i] for i in pos[w]), default=0)
    print('   w%-3d %4d  %3d    %3d + %2d = %3d                        %3d'
          % (w, 0, rdy[k], e, unl[k], e + unl[k], last[w]))
print()
print('actual depth', D, ' model max', max(max((t[i] for i in pos[w]), default=0) + unl[W.index(w)] for w in W))
