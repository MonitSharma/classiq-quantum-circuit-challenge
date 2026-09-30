import random
from sim import symbolic_final
from depth import gate_depth
from sched import gf2_inv_rows
def fixup(gates, required, restarts=3000, seed=0, maxcx=14):
    rows0=symbolic_final(gates)
    base_depth=gate_depth(gates)
    rng=random.Random(seed); best=None
    for r in range(restarts):
        rows=list(rows0); seq=[]
        ok=False
        for step in range(maxcx):
            coord=gf2_inv_rows(rows)
            Cs=[coord(v) for v in required]
            tot=sum(bin(C).count('1')-1 for C in Cs)
            if tot==0: ok=True; break
            cands=[]
            for c in range(9):
                for t in range(9):
                    if c==t: continue
                    d=0
                    for C in Cs:
                        if C>>t&1: d+= -1 if C>>c&1 else 1
                    if d<0 or (d==0 and rng.random()<0.05):
                        cands.append((d+rng.random()*0.9,c,t))
            if not cands: break
            cands.sort(); _,c,t=cands[0] if rng.random()<0.7 else cands[min(len(cands)-1,rng.randrange(3))]
            rows[t]^=rows[c]; seq.append((c,t))
        if not ok: continue
        g2=gates+[(('cx',),c,t) for c,t in seq]
        d=gate_depth(g2)
        if best is None or (d,len(seq))<best[:2]: best=(d,len(seq),seq)
    return base_depth,best
if __name__=="__main__":
    import pickle,sys
    D=pickle.load(open(sys.argv[1],'rb'))
    gates = D['gates'] if isinstance(D,dict) else D[3]
    req=[int(v,0) for v in sys.argv[2].split(',')]
    print(fixup(gates,req))
