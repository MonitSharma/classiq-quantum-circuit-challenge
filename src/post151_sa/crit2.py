import pickle, sys
sys.path.insert(0, '.')
from kdrv import full_gates, profile, KTERMS

DX = pickle.load(open(sys.argv[1], 'rb'))
DY = pickle.load(open(sys.argv[2], 'rb'))
pl, kg = pickle.load(open(sys.argv[3], 'rb'))
gx = full_gates(DX); gy = full_gates(DY)
ex, lx = profile(gx); ey, ly = profile(gy)
e = ex + ey                      # physical loader finish per wire
lu = lx + ly
sigma = kg[0][1]
print('sigma', sigma)
print('loader finish per wire', e)
wt = list(e); l = list(lu)
first = [None] * 18; last = [None] * 18
for g in kg[1:]:
    if g[0] == 'C':
        c, t = g[1], g[2]
        for w in (c, t):
            if first[w] is None: first[w] = max(wt[c], wt[t])
            last[w] = max(wt[c], wt[t]) + 1
        tau = max(wt[c], wt[t]) + 1; wt[c] = wt[t] = tau; l[c] = l[t] = False
    elif g[0] == 'R':
        w = g[1]
        if not l[w]: wt[w] += 1; l[w] = True
        last[w] = wt[w]
T = 0
rows = []
for w in range(18):
    u = sigma[w]
    tot = wt[w] + e[u] - (1 if (l[w] and lu[u]) else 0)
    T = max(T, tot)
    rows.append((tot, w, e[w], first[w], wt[w], e[u], u))
rows.sort(reverse=True)
print('tot  wire side loadfin kfirst kend unload unload_wire')
for tot, w, lf, kf, ke, ul, u in rows[:10]:
    print(f'{tot:4d} {w:4d} {"y" if 9<=w<18 or w in (12,13,14) else "x":>4} {lf:7d} {str(kf):>6} {ke:6d} {ul:6d} {u:9d}')
print('T', T, '  (kernel terms', len(KTERMS), ')')
