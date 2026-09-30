import numpy as np, itertools, sys
from codes import *
from cells import cells_of
from condlp import atoms_for, sparse_rep
side=sys.argv[1]; mask=48 if side=='x' else 32
keys,cid=cells_of(side,mask); nc=len(keys)
code = xcode if side=='x' else ycode; B=bits(code)
labels={c:(sum(B[i] for i in range(3) if c>>i&1)%2) for c in range(1,8)}
def fvals(f): return np.array([(f>>cid[v])&1 for v in range(64)])
cache={}
def cs(tgt, conds):
    key=(tgt.tobytes(),)+tuple(c.tobytes() for c in conds)
    if key in cache: return cache[key]
    Bn=np.array([tgt]+conds)
    k,A=atoms_for(Bn,list(range(1,len(conds)+1)))
    sup,sol=sparse_rep(np.pi*Bn[0].astype(float),A,iters=6); cache[key]=len(sup); return len(sup)
auxes=[int(x) for x in sys.argv[2].split(',')]
res=[]
for f in auxes:
    a=fvals(f); sa=cs(a,[])
    for gc in range(1,8):
        g=labels[gc]; sg=cs(g,[a])
        if sg>35: continue
        for bc in range(1,8):
            if bc==gc: continue
            Lb=labels[bc]; sb=cs(Lb,[a,g])
            if sb>40: continue
            for cc in range(1,8):
                if cc in (gc,bc,gc^bc): continue
                Lc=labels[cc]
                sx=cs((a^Lc),[g,Lb])
                res.append((sa+sg+sb+sx,f,sa,gc,sg,bc,sb,cc,sx))
res.sort()
for r in res[:15]: print("total %d aux %d (a %d) g=L%d|a %d, Lb=L%d|a,g %d, slot a->Lc=L%d via xor|g,Lb %d"%r)
