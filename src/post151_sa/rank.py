"""Rank loader candidates appearing in a portfolio log by the T=117 necessary condition."""
import re, sys
TOUCH = {'y': {1: 31, 2: 40, 4: 25, 8: 33}, 'x': {1: 26, 2: 38, 4: 29, 12: 29}}
side = sys.argv[1]
rows = []
for p in sys.argv[2:]:
    for line in open(p):
        m = re.match(r'OK s(\d+) depth (\d+) rdy \[([^\]]*)\] coords \[([^\]]*)\] W \[([^\]]*)\] proxy \d+', line)
        if not m: continue
        rdy = [int(x) for x in m.group(3).split(',')]
        co = [int(x) for x in m.group(4).split(',')]
        W = [int(x) for x in m.group(5).split(',')]
        tc = TOUCH[side]
        vals = [2*r + tc.get(c, 99) for r, c in zip(rdy, co)]
        rows.append((max(vals), sum(1 for v in vals if v >= max(vals)), sum(rdy), int(m.group(2)), W, rdy, co, vals, line.strip()))
rows.sort(key=lambda t: (t[0], t[1], t[2]))
seen = set()
n = 0
for mx, cnt, sm, dep, W, rdy, co, vals, line in rows:
    k = (tuple(W), tuple(rdy))
    if k in seen: continue
    seen.add(k); n += 1
    print(f'max {mx} atmax {cnt} sum {sm} depth {dep} W {W} rdy {rdy} coords {co} vals {vals}')
    if n >= 12: break
print('total distinct', len(seen), 'of', len(rows))
