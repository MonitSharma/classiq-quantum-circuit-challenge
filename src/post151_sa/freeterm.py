"""Can the x loader host the kernel's pure-x rotations?  Simulate the loader layer by layer and
record, for each pure-x kernel term's form, whether some wire holds that row at some layer."""
import pickle, sys
sys.path.insert(0, '.')
from kdrv import KTERMS, CO, full_gates, profile
R = '../../artifacts/118/recipes/'
D = pickle.load(open(R + 'x_loader_d44.pkl', 'rb'))
g = full_gates(D)
req = D['req']

pure = [m for m in KTERMS if (m & 15) == 0 and (m >> 4) != 0]
print('pure-x kernel terms:', pure)
forms = {}
for m in pure:
    v = 0
    for k in range(4):
        if (m >> (4 + k)) & 1: v ^= req[k]
    forms[m] = v
    print(f'  mask {m:3d} xpart {m>>4:2d} form {v}  popcount {bin(m).count("1")}  co {CO[m]:+.4f}')

# per-layer row simulation (mirrors sim.symbolic_final, including the H "close" rule)
rows = [1 << w for w in range(9)]; closed = set(); wt = [0]*9; lu = [False]*9
hits = {m: [] for m in pure}
for k, x in enumerate(g):
    if x[0][0] == 'cx':
        c, t = x[1], x[2]; m2 = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m2; lu[c] = lu[t] = False
        rows[t] ^= rows[c]
    else:
        w = x[1]
        if not lu[w]: wt[w] += 1; lu[w] = True
        if k > 2:
            tb = [i for i in range(3) if rows[w] >> (6 + i) & 1 and i not in closed]
            if len(tb) == 1:
                closed.add(tb[0]); rows[w] = 1 << (6 + tb[0])
    for m in pure:
        for w in range(9):
            if rows[w] == forms[m]:
                hits[m].append((k, w, wt[w], wt[w]))
print()
for m in pure:
    oncode = [h for h in hits[m] if h[1] in (0, 1, 2, 3)]
    noncode = [h for h in hits[m] if h[1] not in (0, 1, 2, 3)]
    print(f'mask {m:3d} form {forms[m]:4d}: {len(hits[m])} (wire,layer) hits; NON-code wires: {noncode[:6]}')
e, _ = profile(g)
print('  x loader profile', e)
