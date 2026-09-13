"""Rows = cosets of a 3-dim subspace W (reachable by a free CX basis change).
Slot bound: sum over classes of max(max elements of that class in one row,
ceil(size/8)) must be <= 16 for '8 blocks, <=2 classes each' to be possible."""
import sys, itertools; sys.path.insert(0,'src')
from collections import Counter
import two_stage_oracle as ts

def subspaces3():
    seen=set(); out=[]
    for b in itertools.combinations(range(1,64),3):
        S={0}
        for m in range(1,8):
            v=0
            for i in range(3):
                if m>>i&1: v^=b[i]
            S.add(v)
        if len(S)!=8: continue
        key=frozenset(S)
        if key in seen: continue
        seen.add(key); out.append(sorted(S))
    return out
W3=subspaces3()
print('3-dim subspaces:',len(W3))
for name,cls in (('y',ts.ROWCLS),('x',ts.COLCLS)):
    best=[]
    for W in W3:
        # rows = cosets of W
        seen=set(); rows=[]
        for y in range(64):
            if y in seen: continue
            coset=[y^w for w in W]
            seen.update(coset); rows.append([cls[t] for t in coset])
        tot=Counter(x for r in rows for x in r)
        need=0
        for c,n in tot.items():
            need+=max(max(r.count(c) for r in rows), -(-n//8))
        best.append((need,tuple(W)))
    best.sort()
    print(f'{name}: best slot bounds {[b[0] for b in best[:8]]}  (need <=16)')
    print(f'    feasible subspaces: {sum(1 for b in best if b[0]<=16)} of {len(best)}')
    if best[0][0]<=16: print(f'    example W={best[0][1]}')
