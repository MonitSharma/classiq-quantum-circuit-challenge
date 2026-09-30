# Reconstruct the 117 champion's plan and kernel, and print the per-wire accounting that decides T.
import sys, collections
sys.path.insert(0, '.')
exec(open('try9.py').read().split("xs, xl, ys, yl, T =")[0])

DX = load_side('../../artifacts/118/recipes/x_loader_d44.pkl', 'champ', 'tx')
DY = load_side('../../artifacts/118/recipes/y_loader_d46_blkw.pkl', 'runs/po_yF1_s6.txt', 'ty')
sx = valuestable(DX); sy = valuestable(DY)
pl = plan(DX, DY); seq_, W, ST, rdy, unl = pl
svec = [((sx[w] if w < 9 else sy[w - 9]) if (sx[w] if w < 9 else sy[w - 9]) >= 0 else rdy[k]) for k, w in enumerate(W)]
kg = build_kg_s(pl, 'runs/p6_117_16000_2.txt', svec, 117)
rot = collections.Counter(); cxc = collections.Counter(); cxt = collections.Counter()
for g in kg[1:]:
    if g[0] == 'C': cxc[g[1]] += 1; cxt[g[2]] += 1
    else: rot[g[1]] += 1
print('side wire  rdy  valfixed  rot ctrl  tgt  touches  2*rdy+touches   slack@117')
worst = 0
for k, w in enumerate(W):
    tc = rot[w] + cxc[w] + cxt[w]; v = 2 * rdy[k] + tc
    worst = max(worst, v)
    side = 'y' if w >= 9 else 'x'
    print('%s  w%-2d   %2d    %2d     %3d %4d %4d %6d      %4d          %4d%s'
          % (side, w, rdy[k], svec[k], rot[w], cxc[w], cxt[w], tc, v, 117 - v, '   <-- ZERO SLACK' if v == 117 else ''))
print('worst 2*rdy+touches =', worst, ' total kernel CX =', sum(1 for g in kg[1:] if g[0] == 'C'))
print('T=116 would need every wire <= 116; the wires at 117 are short by', worst - 116, 'touch(es)/idle layer(s).')
