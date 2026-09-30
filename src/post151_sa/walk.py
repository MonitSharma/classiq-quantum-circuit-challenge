"""Schedule the Gray-path cover as walkers with the control-availability constraint:
a path on wire w can step only while the wire holding the flipped bit is idle (still at e_j)."""
import sys, collections
sys.path.insert(0, '.')
from kdrv import KTERMS
masks = sorted(KTERMS)
adj = {m: [n for n in masks if bin(m ^ n).count('1') == 1] for m in masks}
deg = {m: len(adj[m]) for m in masks}

def cover(cap):
    unused = set(masks); paths = []
    while unused:
        start = min(unused, key=lambda m: (deg[m], m))
        path = [start]; unused.discard(start)
        while True:
            if cap and len(path) >= cap: break
            nxt = [n for n in adj[path[-1]] if n in unused]
            if not nxt: break
            nxt.sort(key=lambda n: (deg[n], n)); path.append(nxt[0]); unused.discard(nxt[0])
        paths.append(path)
    return sorted(paths, key=len, reverse=True)

def popcount(x): return bin(x).count('1')

for cap in (2, 3, 4, 5, 6):
    paths = cover(cap)
    pc = [popcount(p[0] ^ p[-1]) for p in paths]
    # each path needs its flipped-bit wires pinned idle while it walks
    bitsets = []
    for p in paths:
        s = 0
        for a, b in zip(p, p[1:]): s |= (a ^ b)
        bitsets.append(s)
    # greedy: assign each path a wire; a wire walking cannot serve as a control
    wire_free = [True]*8
    cx = 0; depth = 0
    r = [1 << w for w in range(8)]
    order = sorted(range(len(paths)), key=lambda i: -len(paths[i]))
    assign = {}
    for w in range(8):
        assign[w] = []
    for i in order:
        # pick a wire whose own bit is NOT needed as a control by this path, and that is least loaded
        cand = [w for w in range(8) if not (bitsets[i] >> w & 1)]
        if not cand: cand = list(range(8))
        cand.sort(key=lambda w: (sum(len(paths[j]) for j in assign[w]), w))
        assign[cand[0]].append(i)
    for w in range(8):
        for i in assign[w]:
            p = paths[i]
            cx += popcount(r[w] ^ p[0]) + (len(p) - 1)   # get on path, walk
            r[w] = p[-1]
        cx += popcount(r[w] ^ (1 << w))                  # return home
        r[w] = 1 << w
        depth = max(depth, sum(2*len(paths[i]) for i in assign[w]))
    print(f'cap {cap}: {len(paths)} paths, CX total {cx}, worst-wire op-depth {depth}')
