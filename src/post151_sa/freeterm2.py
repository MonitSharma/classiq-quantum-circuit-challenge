"""Same test as freeterm.py but for the y side (and any loader): can this loader host the kernel's
pure-side rotations?  Simulates the loader layer by layer and records which wire holds each form."""
import pickle, sys
sys.path.insert(0, '.')
from kdrv import KTERMS, CO, full_gates, profile
side = sys.argv[1]
if side == 'y':
    D = pickle.load(open('../../artifacts/118/recipes/y_loader_d46_blkw.pkl', 'rb'))
    pure = [m for m in KTERMS if (m >> 4) == 0 and (m & 15) != 0]
    bits, shift = 4, 0
else:
    D = pickle.load(open('../../artifacts/118/recipes/x_loader_d44.pkl', 'rb'))
    pure = [m for m in KTERMS if (m & 15) == 0 and (m >> 4) != 0]
    bits, shift = 0, 4
req = D['req']
print(f'{side}: {len(pure)} pure terms', pure)
forms = {}
for m in pure:
    v = 0
    for k in range(4):
        if (m >> (shift + k)) & 1: v ^= req[k]
    forms[m] = v
g = full_gates(D)
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
            if rows[w] == forms[m]: hits[m].append((k, w, wt[w]))
e, _ = profile(g)
code = set()
for b in range(1, 16):
    v = 0
    for k in range(4):
        if b >> k & 1: v ^= req[k]
    code.add(v)
for m in pure:
    noncode = [h for h in hits[m] if rows_final.get(h[1], None) not in code] if False else [h for h in hits[m] if h[1] >= 4]
    print(f'  mask {m:3d} form {forms[m]:4d} popcount {bin(m).count("1")}: {len(hits[m])} hits; wires>=4: {noncode[:5]}')
print('  loader profile', e)
