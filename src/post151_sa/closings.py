import pickle, sys
sys.path.insert(0, '.')
D = pickle.load(open(sys.argv[1], 'rb'))
g = D['gates']
# ASAP layer per gate, tracking rows and closing H's
wt = [0] * 9
rows = [1 << w for w in range(9)]
closed = {}
pend_rot = {}
last_touch = [0] * 9
for gg in g:
    if gg[0][0] == 'cx':
        c, t = gg[1], gg[2]
        l = max(wt[c], wt[t]) + 1
        wt[c] = wt[t] = l
        rows[t] ^= rows[c]
        last_touch[c] = last_touch[t] = l
        for w in (c, t):
            pass
    elif gg[0][0] == 'h':
        w = gg[1]; l = wt[w] + 1; wt[w] = l; last_touch[w] = l
        # a closing H: before it the wire carried exactly one open target bit
        tb = [i for i in range(3) if rows[w] >> (6 + i) & 1 and i not in closed]
        ob = [j for j in range(3) if j not in closed and j != (tb[0] if tb else -1)]
        if len(tb) == 1 and not any(rows[w] >> (6 + j) & 1 for j in ob):
            closed[tb[0]] = l
            rows[w] = 1 << (6 + tb[0])
    else:
        w = gg[1]; l = wt[w] + 1; wt[w] = l; last_touch[w] = l
print('closing layers', closed, 'depth', max(wt))
print('last touch per wire', last_touch)
req = D['req']
print('req', req)
span = {}
for b in range(1, 16):
    v = 0
    for k in range(4):
        if b >> k & 1: v ^= req[k]
    span[v] = b
print('rows at end', rows)
print('in-span wires', [(w, rows[w], last_touch[w]) for w in range(9) if rows[w] in span])
