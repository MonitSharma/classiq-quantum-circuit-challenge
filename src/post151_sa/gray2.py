"""Cost a complete Gray-path kernel: walk each path on its own wire, then return every wire home.
Counts total CX against the beam's 91-94."""
import sys, collections
sys.path.insert(0, '.')
from kdrv import KTERMS
masks = sorted(KTERMS)
adj = {m: [n for n in masks if bin(m ^ n).count('1') == 1] for m in masks}
deg = {m: len(adj[m]) for m in masks}

def cover(cap=None):
    unused = set(masks); paths = []
    while unused:
        start = min(unused, key=lambda m: (deg[m], m))
        path = [start]; unused.discard(start)
        while True:
            cur = path[-1]
            nxt = [n for n in adj[cur] if n in unused]
            if cap and len(path) >= cap: break
            if not nxt: break
            nxt.sort(key=lambda n: (deg[n], n))
            path.append(nxt[0]); unused.discard(nxt[0])
        paths.append(path)
    return sorted(paths, key=len, reverse=True)

def popcount(x): return bin(x).count('1')

for cap, label in ((None, 'greedy-longest'), (8, 'balanced cap 8'), (4, 'balanced cap 4')):
    paths = cover(cap)
    # assign paths to wires 0..7; wire w home = 1<<w
    r = [1 << w for w in range(8)]
    cx = 0
    for i, p in enumerate(paths):
        if i >= 8: break
        w = i % 8
        cx += popcount(r[w] ^ p[0])          # get onto the path head
        r[w] = p[0]
        cx += len(p) - 1                      # walk
        r[w] = p[-1]
    cx += sum(popcount(r[w] ^ (1 << w)) for w in range(8))   # return home
    print(f'{label}: {len(paths)} paths lengths {[len(p) for p in paths]}')
    print(f'   forward+setup CX {cx - sum(popcount(r[w] ^ (1<<w)) for w in range(8))}, '
          f'return CX {sum(popcount(r[w] ^ (1<<w)) for w in range(8))}, TOTAL {cx}')
