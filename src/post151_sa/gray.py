"""Can the 63 kernel rotations be scheduled by a Gray-path (walker) network instead of the beam's
XOR cloud?  A step between two forms differing in one bit costs 1 CX + 1 rotation on one wire."""
import pickle, sys, collections
sys.path.insert(0, '.')
from kdrv import KTERMS
masks = sorted(KTERMS)
print('kernel terms:', len(masks), 'popcount hist', sorted(collections.Counter(bin(m).count('1') for m in masks).items()))

# adjacency: differ in exactly one bit
adj = {m: [n for n in masks if bin(m ^ n).count('1') == 1] for m in masks}
deg = {m: len(adj[m]) for m in masks}
print('degree hist', sorted(collections.Counter(deg.values()).items()))
print('isolated (no one-bit neighbour):', [m for m in masks if deg[m] == 0])

# greedy path cover: repeatedly take the longest simple path from the lowest-degree unused node
unused = set(masks); paths = []
while unused:
    start = min(unused, key=lambda m: (deg[m], m))
    path = [start]; unused.discard(start)
    while True:
        cur = path[-1]
        nxt = [n for n in adj[cur] if n in unused]
        if not nxt: break
        nxt.sort(key=lambda n: (deg[n], n))
        path.append(nxt[0]); unused.discard(nxt[0])
    paths.append(path)
paths.sort(key=len, reverse=True)
print(f'path cover: {len(paths)} paths, lengths {[len(p) for p in paths]}')
print(f'  steps (CX) = {sum(len(p)-1 for p in paths)}; rotations = {len(masks)}')
print(f'  lower bound on kernel span with full parallelism: '
      f'{sum(len(p)-1 for p in paths) + len(masks)} ops over 8 wires '
      f'>= {(sum(len(p)-1 for p in paths) + len(masks) + 7)//8} layers')
for i, p in enumerate(paths[:10]):
    print(f'  path {i}: len {len(p)} start {p[0]} end {p[-1]}')
