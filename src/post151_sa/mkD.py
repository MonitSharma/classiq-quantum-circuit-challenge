import sys, pickle, numpy as np
from codes import *
from condlp import atoms_for, sparse_rep
from sched2 import LayerLoader
from depth import gate_depth
import random
def makeD(side, cols, kind, order, moved_anc=True):
    code = xcode if side=='x' else ycode
    B=bits(code)
    Bn=np.array([sum(B[i] for i in range(3) if cols[j]>>i&1)%2 for j in range(3)])
    newcode=[int(Bn[0][v]|(Bn[1][v]<<1)|(Bn[2][v]<<2)) for v in range(64)]
    if kind=='seq': cond={order[0]:[],order[1]:[order[0]],order[2]:[order[0],order[1]]}
    else: cond={order[0]:[],order[1]:[order[0]],order[2]:[order[0]]}
    targets={}
    for i in range(3):
        keys,A=atoms_for(Bn,cond[i])
        sup,sol=sparse_rep(np.pi*Bn[i].astype(float),A,iters=10)
        par={}
        for k,coef in zip(sup,sol):
            s,sub=keys[k]; mask=(1<<(6+i))|s
            for j in sub: mask|=1<<(6+j)
            par[mask]=par.get(mask,0.0)+coef
        targets[i]=par
    Minv={}
    for i in range(3):
        for combo in range(1,8):
            v=0
            for j in range(3):
                if combo>>j&1: v^=cols[j]
            if v==(1<<i): Minv[i]=combo
    req=[0x30 if side=='x' else 0x20]+[sum(1<<(6+j) for j in range(3) if Minv[i]>>j&1) for i in range(3)]
    anc={6,7,8}; allw=set(range(9))
    moved={'x':[False,False,True,True],'y':[False,True,True,True]}[side]
    al=[anc if (m and moved_anc) else allw for m in moved]
    # initial gates by greedy
    rng=random.Random(1); best=None
    for r in range(200):
        L=LayerLoader(targets, random.Random(rng.random()), w_setup=rng.uniform(0.1,3), w_d2=rng.uniform(0,1), noise=rng.choice([0.02,0.1,0.3]))
        d=L.run()
        if d is None: continue
        dd=gate_depth(L.gates)
        if best is None or dd<best[0]: best=(dd,L.gates)
    from fixup2 import fixup2
    fx=fixup2(best[1],req,al,restarts=300,seed=3)
    return dict(side=side,cols=cols,cond=cond,targets=targets,gates=best[1],fix=fx[2],req=req,al=al,newcode=newcode,depth=fx[0])
if __name__=="__main__":
    side=sys.argv[1]; cols=tuple(int(c) for c in sys.argv[2].split(',')); kind=sys.argv[3]; order=tuple(int(c) for c in sys.argv[4]); out=sys.argv[5]
    D=makeD(side,cols,kind,order)
    print({i:len(D['targets'][i]) for i in range(3)},"greedy+fix depth",D['depth'])
    pickle.dump(D,open(out,'wb'))
