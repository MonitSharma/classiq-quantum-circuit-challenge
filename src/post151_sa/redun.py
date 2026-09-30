"""Cancel redundant CX pairs in a kernel gate list (a CX(c,t) repeated with nothing
touching c or t in between cancels), then re-time ASAP and report T."""
import pickle, sys
sys.path.insert(0, '.')

R = '../../artifacts/118/recipes/'
pl, kg = pickle.load(open(R + 'kernel_plan_and_gates_118.pkl', 'rb'))
seq, W, ST, rdy, unl = pl
ex = [43, 35, 44, 44, 42, 42, 42, 44, 40]
ey = [35, 45, 39, 45, 44, 44, 43, 46, 45]
e = ex + ey

def cancel(body):
    body = list(body)
    changed = True
    while changed:
        changed = False
        seen = {}          # (c,t) -> index
        byw = {w: set() for w in range(18)}
        dead = set()
        for j, g in enumerate(body):
            if g[0] == 'C':
                c, t = g[1], g[2]
                key = (c, t)
                if key in seen:
                    i = seen.pop(key); byw[c].discard(key); byw[t].discard(key)
                    dead.add(i); dead.add(j); changed = True
                    continue
                ws = (c, t)
            else:
                ws = (g[1],)
            for w in ws:
                for key in list(byw[w]):
                    seen.pop(key, None)
                    byw[key[0]].discard(key); byw[key[1]].discard(key)
            if g[0] == 'C':
                key = (g[1], g[2])
                seen[key] = j; byw[g[1]].add(key); byw[g[2]].add(key)
        body = [g for j, g in enumerate(body) if j not in dead]
    return body

def sched(body):
    avail = list(e); last = list(e); lu = [False] * 18
    n1q = 0
    for g in body:
        if g[0] == 'C':
            c, t = g[1], g[2]; tau = max(avail[c], avail[t]) + 1
            avail[c] = avail[t] = tau; lu[c] = lu[t] = False; last[c] = last[t] = tau
        else:
            w = g[1]
            if lu[w]: tau = avail[w]
            else: tau = avail[w] + 1
            avail[w] = tau; lu[w] = True; last[w] = tau
    return last

def rep(tag, body):
    last = sched(body)
    ncx = sum(1 for g in body if g[0] == 'C')
    tot = max(last[w] + e[w] for w in range(18))
    print(f'{tag}: gates {len(body)} cx {ncx} T {tot}')
    print('   per-wire last', {w: last[w] for w in W})
    print('   last+e        ', {w: last[w] + e[w] for w in W})
    return tot, last

body = kg[1:]
rep('original     ', body)
b2 = cancel(body)
rep('cancelled    ', b2)
b3 = [g for g in b2 if not (g[0] == 'C' and g[1] == g[2])]
rep('cancel+self  ', b3)
pickle.dump((pl, [kg[0]] + b3), open('runs/kg118_red.pkl', 'wb'))
