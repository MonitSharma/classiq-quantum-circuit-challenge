import random
from sim import symbolic_final
from depth import gate_depth
from sched import gf2_inv_rows
def fixup2(gates, required, allowed, restarts=4000, seed=0, maxcx=20):
    """required: list of vectors; allowed: list of sets of wires (block-local) for each vector"""
    rows0=symbolic_final(gates); rng=random.Random(seed); best=None
    def h(rows):
        coord=gf2_inv_rows(rows); tot=0
        for v,A in zip(required,allowed):
            C=coord(v); pc=bin(C).count('1')
            tot+=min(pc-1+(0 if (C>>w)&1 else 1) for w in A)
        return tot
    def done(rows):
        pos={}
        for v,A in zip(required,allowed):
            ws=[w for w in A if rows[w]==v]
            if not ws: return False
        return True
    for r in range(restarts):
        rows=list(rows0); seq=[]
        for step in range(maxcx):
            if done(rows): break
            cur=h(rows); cands=[]
            for c in range(9):
                for t in range(9):
                    if c==t: continue
                    rows[t]^=rows[c]; hv=h(rows); rows[t]^=rows[c]
                    cands.append((hv-cur+rng.random()*0.99,c,t))
            cands.sort()
            k=0 if rng.random()<0.6 else rng.randrange(min(4,len(cands)))
            _,c,t=cands[k]; rows[t]^=rows[c]; seq.append((c,t))
        if not done(rows): continue
        d=gate_depth(gates+[(('cx',),c,t) for c,t in seq])
        if best is None or (d,len(seq))<best[:2]: best=(d,len(seq),seq)
    return best
