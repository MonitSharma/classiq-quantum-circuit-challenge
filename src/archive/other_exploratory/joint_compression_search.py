"""Search for a logo-preserving 6-bit compression with local features.

F: {0,1}^12 -> {0,1}^6, each bit h_i reading only the wires in support S_i.
Feasible iff every fibre of F is logo-constant.
cost = sum over fibres of min(#logo0, #logo1);  cost 0 == feasible.
"""
import sys, itertools, random, math, time, json; sys.path.insert(0,'src')
import numpy as np, two_stage_oracle as ts

LOGO=np.array([[1 if ts.logo(x,y) else 0 for x in range(64)] for y in range(64)],dtype=np.int8).ravel()
# point index p = y*64 + x ; wires: y bits 0..5 -> bits 6..11 of p, x bits 0..5 -> bits 0..5
def proj(sup):
    """for every point, the index into that feature's 2^|sup| truth table"""
    idx=np.zeros(4096,dtype=np.int64)
    for k,w in enumerate(sup):
        bit=(np.arange(4096)>>w)&1
        idx |= bit<<k
    return idx

def cost_of(tables,idxs):
    F=np.zeros(4096,dtype=np.int64)
    for i,(t,ix) in enumerate(zip(tables,idxs)):
        F |= (t[ix].astype(np.int64))<<i
    n1=np.bincount(F[LOGO==1],minlength=64)
    n0=np.bincount(F[LOGO==0],minlength=64)
    return int(np.minimum(n0,n1).sum())

def anneal(sups,seed,budget):
    rng=random.Random(seed); np.random.seed(seed&0xffff)
    idxs=[proj(s) for s in sups]
    tabs=[np.random.randint(0,2,size=1<<len(s)).astype(np.int8) for s in sups]
    cur=cost_of(tabs,idxs); best=cur; T=60.0; t0=time.time()
    while time.time()-t0<budget and best>0:
        i=rng.randrange(len(tabs)); j=rng.randrange(len(tabs[i]))
        tabs[i][j]^=1
        c=cost_of(tabs,idxs)
        if c<=cur or rng.random()<math.exp(-(c-cur)/max(T,0.5)):
            cur=c
            if c<best: best=c
        else:
            tabs[i][j]^=1
        T*=0.9997
        if T<0.5: T=60.0
    return best,tabs

XW=list(range(6)); YW=list(range(6,12))
FAMS={
 'mixed 5x+1y / 1x+5y':[ (0,1,2,3,4,6),(1,2,3,4,5,8),(0,2,3,4,5,10),
                          (0,6,7,8,9,10),(2,7,8,9,10,11),(4,6,7,8,10,11) ],
}
print(f'logo: {int(LOGO.sum())} ones of 4096\n')
res={}
for nm,sups in FAMS.items():
    b=None
    for seed in range(3):
        r,_=anneal(sups,seed,45)
        b=r if b is None else min(b,r)
        if b==0: break
    res[nm]=b
    print(f'{nm:34s} best cost {b:5d}   {"FEASIBLE" if b==0 else "infeasible (points that must collide)"}',flush=True)
json.dump(res,open(sys.argv[1],'w'))
