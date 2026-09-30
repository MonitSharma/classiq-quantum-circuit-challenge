"""Can the classes be packed into 2^k equal blocks with <= 2^m classes each?

k in-place code wires split the 64 values into 2^k blocks of 64/2^k.
m loaded ancilla bits must separate the classes inside each block.
Any equal-size partition is realisable by some reversible transform, so this
is a pure feasibility question on the class-size multiset.
"""
import sys; sys.path.insert(0,'src')
from collections import Counter
from functools import lru_cache
import two_stage_oracle as ts

def feasible(sizes, nblocks, cap):
    bs = sum(sizes)//nblocks
    sizes = tuple(sorted(sizes, reverse=True))
    seen=set()
    def rec(rem, b):
        if b==0: return all(v==0 for v in rem)
        key=(rem,b)
        if key in seen: return False
        seen.add(key)
        idx=[i for i,v in enumerate(rem) if v>0]
        # choose <=cap classes to fill one block of size bs
        import itertools
        for r in range(1, cap+1):
            for combo in itertools.combinations(idx, r):
                # distribute bs among combo, each >=1, <= rem
                def dist(pos, left, acc):
                    if pos==len(combo):
                        if left==0: yield tuple(acc)
                        return
                    hi=min(rem[combo[pos]], left-(len(combo)-pos-1))
                    for take in range(1, hi+1):
                        yield from dist(pos+1, left-take, acc+[take])
                for take in dist(0, bs, []):
                    nr=list(rem)
                    for c,t in zip(combo,take): nr[c]-=t
                    if rec(tuple(nr), b-1): return True
        return False
    return rec(sizes, nblocks)

for name,cls in (('y',ts.ROWCLS),('x',ts.COLCLS)):
    sizes=sorted(Counter(cls).values(), reverse=True)
    print(f'{name}: class sizes {sizes}')
    for k,m in ((3,1),(2,2),(4,0),(2,1)):
        nb=1<<k; cap=1<<m
        if 64%nb: continue
        ok=feasible(sizes, nb, cap)
        cost=128*m   # ancilla bits; in-place wires priced separately
        print(f'   k={k} in-place wires, m={m} ancilla bits: blocks of {64//nb}, <= {cap} classes  -> {"FEASIBLE" if ok else "infeasible"}')
