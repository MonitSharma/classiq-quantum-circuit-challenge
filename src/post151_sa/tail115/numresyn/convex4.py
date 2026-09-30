"""convex3.py file.qasm : for every qubit triple grow maximal convex subcircuits confined to the triple
(closure-based growth from each CX seed). Reports the largest blocks by CX count."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, json, itertools
from blockscan import parse, layers

ops = parse(sys.argv[1]); n = len(ops); lay, D = layers(ops)
# DAG edges: wire successor
succ = [[] for _ in range(n)]; pred = [[] for _ in range(n)]; last = [None] * 18
for i, o in enumerate(ops):
    for q in o[1]:
        if last[q] is not None: succ[last[q]].append(i); pred[i].append(last[q])
        last[q] = i
desc = [0] * n
for i in range(n - 1, -1, -1):
    m = 0
    for j in succ[i]: m |= (1 << j) | desc[j]
    desc[i] = m
anc = [0] * n
for i in range(n):
    m = 0
    for j in pred[i]: m |= (1 << j) | anc[j]
    anc[i] = m
qmask = []
for o in ops:
    qmask.append(sum(1 << q for q in o[1]))

def bits(x):
    while x:
        b = x & -x; yield b.bit_length() - 1; x ^= b

def closure(S):
    d = 0; a = 0
    for i in bits(S): d |= desc[i]; a |= anc[i]
    return S | (d & a)

def grow(seed, T):
    tm = sum(1 << q for q in T); S = 1 << seed
    changed = True
    while changed:
        changed = False
        nb = 0
        for i in bits(S):
            for j in succ[i] + pred[i]:
                if not (S >> j) & 1 and (qmask[j] & ~tm) == 0: nb |= 1 << j
        for j in bits(nb):
            C = closure(S | (1 << j))
            if all((qmask[k] & ~tm) == 0 for k in bits(C & ~S)):
                S = C; changed = True
    return S

seen = {}
for i, o in enumerate(ops):
    if o[0] != 'cx': continue
    a, b = o[1]
    for c in range(18):
        for c2 in range(c + 1, 18):
            if c in (a, b) or c2 in (a, b): continue
            T = tuple(sorted((a, b, c, c2)))
            S = grow(i, T)
            if S not in seen: seen[S] = T
res = []
for S, T in seen.items():
    g = list(bits(S)); ncx = sum(ops[k][0] == 'cx' for k in g)
    used = set(q for k in g for q in ops[k][1])
    if len(used) < 4: continue
    span = max(lay[k] for k in g) - min(lay[k] for k in g) + 1
    res.append(dict(q=list(T), g=g, ncx=ncx, span=span, t0=min(lay[k] for k in g)))
res.sort(key=lambda r: (-r['ncx'], r['span']))
# keep maximal (not subset of another)
keep = []
for r in res:
    s = set(r['g'])
    if any(s <= set(k['g']) for k in keep): continue
    keep.append(r)
from collections import Counter
print('maximal 4q blocks', len(keep), 'cx hist', sorted(Counter(r['ncx'] for r in keep).items()))
for r in keep[:25]: print(r['q'], 'cx', r['ncx'], 'span', r['span'], 't0', r['t0'])
json.dump(keep, open(f'{WK}/convex4.json', 'w'))
