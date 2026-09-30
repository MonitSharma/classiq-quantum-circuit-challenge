"""Validated free-term test: count a hit only if it occurs AFTER every label has been closed
(so the wire's row is a form in the final variable space) and on a wire that is NOT a code wire
(a rotation on a code wire before its freeze would delay the very ready time it should save)."""
import pickle, sys
sys.path.insert(0, '.')
from kdrv import KTERMS, full_gates, profile
side = sys.argv[1]
if side == 'y':
    D = pickle.load(open('../../artifacts/118/recipes/y_loader_d46_blkw.pkl', 'rb'))
    pure = [m for m in KTERMS if (m >> 4) == 0 and (m & 15) != 0]; shift = 0
else:
    D = pickle.load(open('../../artifacts/118/recipes/x_loader_d44.pkl', 'rb'))
    pure = [m for m in KTERMS if (m & 15) == 0 and (m >> 4) != 0]; shift = 4
req = D['req']
forms = {}
for m in pure:
    v = 0
    for k in range(4):
        if (m >> (shift + k)) & 1: v ^= req[k]
    forms[m] = v
g = full_gates(D)
rows = [1 << w for w in range(9)]; closed = set(); wt = [0]*9; lu = [False]*9
last_close = -1
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
                closed.add(tb[0]); rows[w] = 1 << (6 + tb[0]); last_close = k
print(f'{side}: {len(pure)} pure terms; last label closed at gate {last_close} of {len(g)}')
e, _ = profile(g)
# final rows decide which wires are code wires
final = [1 << w for w in range(9)]; cl = set()
for k, x in enumerate(g):
    if x[0][0] == 'cx': final[x[2]] ^= final[x[1]]
    else:
        w = x[1]
        if k > 2:
            tb = [i for i in range(3) if final[w] >> (6 + i) & 1 and i not in cl]
            if len(tb) == 1: cl.add(tb[0]); final[w] = 1 << (6 + tb[0])
span = set()
for b in range(1, 16):
    v = 0
    for k in range(4):
        if b >> k & 1: v ^= req[k]
    span.add(v)
code = {w for w in range(9) if final[w] in span}
print('  code wires:', sorted(code), ' profile', e)
# replay, counting only post-close hits
rows = [1 << w for w in range(9)]; closed = set(); wt = [0]*9; lu = [False]*9
for m in pure:
    good = []
    for k, x in enumerate(g):
        if x[0][0] == 'cx':
            c, t = x[1], x[2]; m2 = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = m2; lu[c] = lu[t] = False
            rows[t] ^= rows[c]
        else:
            w = x[1]
            if not lu[w]: wt[w] += 1; lu[w] = True
            if k > 2:
                tb = [i for i in range(3) if rows[w] >> (6 + i) & 1 and i not in closed]
                if len(tb) == 1: closed.add(tb[0]); rows[w] = 1 << (6 + tb[0])
        if k > last_close:
            for w in range(9):
                if rows[w] == forms[m] and w not in code:
                    good.append((k, w, wt[w], e[w]))
    print(f'  mask {m:3d} form {forms[m]:4d} pc {bin(m).count("1")}: post-close NON-code hits {good[:6]}')
