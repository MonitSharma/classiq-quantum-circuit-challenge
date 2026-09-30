"""Re-time an existing kernel gate list as early as possible (ASAP), preserving dependency order."""
import pickle, sys, os
sys.path.insert(0, '.')
from kdrv import KTERMS, CO, full_gates, assemble

R = '../../artifacts/118/recipes/'
DX = pickle.load(open(R + 'x_loader_d44.pkl', 'rb'))
DY = pickle.load(open(R + 'y_loader_d46_blkw.pkl', 'rb'))
pl, kg = pickle.load(open(R + 'kernel_plan_and_gates_118.pkl', 'rb'))
seq, W, ST, rdy, unl = pl

def unwire(g): return (g[1], g[2]) if g[0] == 'C' else (g[1],)

def sched(body, e, merge1q=True):
    avail = list(e); lu = [False]*18; tau = []
    last = list(e)
    for g in body:
        ws = unwire(g)
        if g[0] == 'C':
            t = max(avail[w] for w in ws) + 1
            for w in ws: avail[w] = t; lu[w] = False
        else:
            w = ws[0]
            if merge1q and lu[w]: t = avail[w]
            else: t = avail[w] + 1
            avail[w] = t; lu[w] = True
        tau.append(t)
        for w in ws: last[w] = t
    return tau, last, avail

def report(tag, last, T=None):
    tot = [last[w] + unl[pl[1].index(w)] if w in W else 2*last[w] for w in range(18)]
    # proper: unload wire is sigma[w]
    sig = kg[0][1]
    ex = [43,35,44,44,42,42,42,44,40]
    ey = [35,45,39,45,44,44,43,46,45]
    e = ex + ey
    best = 0
    for w in range(18):
        v = last[w] + e[sig[w]]
        if v > best: best = v
    print(tag, 'T =', best, ' maxlast', max(last))

body = kg[1:]
ex = [43,35,44,44,42,42,42,44,40]
ey = [35,45,39,45,44,44,43,46,45]
e = ex + ey

tau, last, avail = sched(body, e, merge1q=True)
report('ASAP(merge1q)', last)
tau2, last2, _ = sched(body, e, merge1q=False)
report('ASAP(sep1q)  ', last2)

# also strip redundant adjacent identical CX pairs and retime
stripped = []
i = 0
while i < len(body):
    if i + 1 < len(body) and body[i][0] == 'C' and body[i+1][0] == 'C' and body[i][1:] == body[i+1][1:]:
        i += 2; continue
    stripped.append(body[i]); i += 1
print('body', len(body), '-> stripped', len(stripped))
if len(stripped) != len(body):
    t3, last3, _ = sched(stripped, e, merge1q=True)
    report('strip+ASAP   ', last3)
