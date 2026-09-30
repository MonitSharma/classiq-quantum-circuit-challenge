# Measure the true unload tail per wire from the assembled champion and test  tail = D - first + 1.
# Deeper point:  T >= rdy_w + touches_w + tail_w  and  rdy_w + tail_w = last_w - first_w + D + 1,
# so the quantity to minimise is how WIDE a window each code wire is touched in.
import sys, pickle
sys.path.insert(0, '.')
exec(open('try9.py').read().split("xs, xl, ys, yl, T =")[0])
from qa import parse, layers

DX = load_side('../../artifacts/118/recipes/x_loader_d44.pkl', 'champ', 'tx')
DY = load_side('../../artifacts/118/recipes/y_loader_d46_blkw.pkl', 'runs/po_yF1_s6.txt', 'ty')
gx = full_gates(DX); gy = full_gates(DY)
nL = len(gx) + len(gy)
n, gg = parse('../../artifacts/117/conditional_loader_117.qasm')
Kops = gg[nL:len(gg) - nL]
loader = gg[:nL]; inv = gg[len(gg) - nL:]
print('gates: loader %d  kernel %d  inverse %d' % (len(loader), len(Kops), len(inv)))

d = [0]*18; first = [None]*18; rdy = [0]*18; kend = [0]*18; fin = [0]*18
def step(g, tag):
    qs = [g[1][0], g[1][1]] if g[0] == 'cx' else [g[1][0]]
    l = max(d[q] for q in qs) + 1
    for q in qs:
        d[q] = l
        if first[q] is None: first[q] = l
        if tag == 'L': rdy[q] = l
        elif tag == 'K': kend[q] = l
        fin[q] = l
for g in loader: step(g, 'L')
for g in Kops: step(g, 'K')
for g in inv: step(g, 'I')
D = max(d)
print('assembled depth', D)

pl_W = [10, 9, 14, 17, 1, 0, 2, 3]
XPH = [0, 1, 2, 3, 4, 5, 15, 16, 17]; YPH = [6, 7, 8, 9, 10, 11, 12, 13, 14]
print()
print('plan  phys  first  rdy  kernel-end  circuit-end   tail = end-kernel   D-first+1')
for k, w in enumerate(pl_W):
    q = XPH[w] if w < 9 else YPH[w - 9]
    tail = fin[q] - kend[q]
    print('  w%-3d %4d   %2s   %2d     %2d          %3d          %3d            %3d'
          % (w, q, first[q], rdy[q], kend[q], fin[q], tail, 0))
