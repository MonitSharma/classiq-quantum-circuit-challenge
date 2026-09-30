# Re-time the verified 117 kernel schedule to its compressed times and emit a T=116 circuit.
# Validity argument: the op list is a sequence of CX (single op on both wires) and rotations.  Preserving
# the per-wire order of ops preserves, on every wire, the exact sequence of linear forms it holds, hence
# every rotation still fires on a wire holding its own mask.  Only the layer placement changes.
import sys, pickle
sys.path.insert(0, '.')
exec(open('try9.py').read().split("xs, xl, ys, yl, T =")[0])

DX = load_side('../../artifacts/118/recipes/x_loader_d44.pkl', 'champ', 'tx')
DY = load_side('../../artifacts/118/recipes/y_loader_d46_blkw.pkl', 'runs/po_yF1_s6.txt', 'ty')
sx = valuestable(DX); sy = valuestable(DY)
pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
svec = [((sx[w] if w < 9 else sy[w - 9]) if (sx[w] if w < 9 else sy[w - 9]) >= 0 else rdy[k]) for k, w in enumerate(W)]
kg = build_kg_s(pl, 'runs/p6_117_16000_2.txt', svec, 117)
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

order = sorted(range(len(body)), key=lambda i: (t[i], i))
newkg = [kg[0]] + [body[i] for i in order]
T_need = max(max((t[i] for i in pos[w]), default=0) + unl[W.index(w)] for w in W)
print('compressed times: max =', max(t), ' implied T =', T_need)
out = sys.argv[1] if len(sys.argv) > 1 else 'runs/c116.qasm'
D, ncx = assemble(DX, DY, newkg, out)
print('ASSEMBLED', out, 'depth', D, 'cx', ncx, flush=True)
pickle.dump((pl, newkg), open(out.replace('.qasm', '.pkl'), 'wb'))
