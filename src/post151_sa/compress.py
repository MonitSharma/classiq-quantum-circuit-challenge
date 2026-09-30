# Is the KNOWN 117 kernel schedule compressible to T=116 by re-timing alone?
# If we keep the per-wire op order and the CX pairings fixed, every wire's FORM sequence is preserved
# exactly, so any time assignment that respects (a) one op per wire per layer, (b) CX endpoints equal,
# (c) per-wire release times, is a VALID schedule.  The minimum such T is a longest-path computation.
import sys
sys.path.insert(0, '.')
exec(open('try9.py').read().split("xs, xl, ys, yl, T =")[0])

DX = load_side('../../artifacts/118/recipes/x_loader_d44.pkl', 'champ', 'tx')
DY = load_side('../../artifacts/118/recipes/y_loader_d46_blkw.pkl', 'runs/po_yF1_s6.txt', 'ty')
sx = valuestable(DX); sy = valuestable(DY)
pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
svec = [((sx[w] if w < 9 else sy[w - 9]) if (sx[w] if w < 9 else sy[w - 9]) >= 0 else rdy[k]) for k, w in enumerate(W)]
src = sys.argv[1] if len(sys.argv) > 1 else 'runs/p6_117_16000_2.txt'
kg = build_kg_s(pl, src, svec, 117)

# ops after the initial permutation: ('C', c, t) is a CX between plan wires c,t; ('R', w, theta) a rotation.
ops = []
for g in kg[1:]:
    if g[0] == 'C': ops.append(('C', g[1], g[2]))
    else: ops.append(('R', g[1], None))
pos = {w: [i for i, o in enumerate(ops) if w in o[1:]] for w in W}
rel = {}
for i, o in enumerate(ops):
    w = o[1]
    rel[i] = svec[W.index(w)] if o[0] == 'R' else rdy[W.index(w)]
    if o[0] == 'C':
        rel[i] = max(rel[i], rdy[W.index(o[2])])
t = dict(rel)
# A CX is ONE op occupying both of its wires in the same layer, so the only constraints are the
# per-wire chains (consecutive ops on a wire at least one layer apart) and the release times.
for _ in range(4000):
    changed = False
    for w in W:                                   # per-wire chain: consecutive ops >= 1 layer apart
        ws = pos[w]
        for a, b in zip(ws, ws[1:]):
            if t[b] < t[a] + 1: t[b] = t[a] + 1; changed = True
    if not changed: break

end = {w: max((t[i] for i in pos[w]), default=0) for w in W}
Tn = max(end[W[k]] + unl[k] for k in range(8))
print('op count', len(ops), 'CX', sum(1 for o in ops if o[0] == 'C'), 'rot', sum(1 for o in ops if o[0] == 'R'))
for k, w in enumerate(W):
    print('  w%-3d rdy %2d  unload %2d  kernel-end %2d   end+unload %3d' % (w, rdy[k], unl[k], end[w], end[w] + unl[k]))
print('COMPRESSED T for this exact op order =', Tn)
print('=> ' + ('RE-TIMING TO ' + str(Tn) + ' IS VALID — rebuild it!' if Tn < 117 else 'no gain from re-timing alone'))
