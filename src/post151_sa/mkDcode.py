import sys, pickle, numpy as np, random
from codes import *
from cells import cells_of
from condlp import atoms_for, sparse_rep
from sched2 import LayerLoader
from depth import gate_depth
from fixup2 import fixup2
def makeD_code(side, fs, kind, order, req_al=None):
    mask=48 if side=='x' else 32
    keys,cid=cells_of(side,mask)
    Bn=np.array([[ (fs[j]>>cid[v])&1 for v in range(64)] for j in range(3)])
    newcode=[int(Bn[0][v]|(Bn[1][v]<<1)|(Bn[2][v]<<2)) for v in range(64)]
    if kind=='seq': cond={order[0]:[],order[1]:[order[0]],order[2]:[order[0],order[1]]}
    else: cond={order[0]:[],order[1]:[order[0]],order[2]:[order[0]]}
    targets={}
    for i in range(3):
        ks,A=atoms_for(Bn,cond[i]); sup,sol=sparse_rep(np.pi*Bn[i].astype(float),A,iters=10)
        par={}
        for k,coef in zip(sup,sol):
            s,sub=ks[k]; m=(1<<(6+i))|s
            for j in sub: m|=1<<(6+j)
            par[m]=par.get(m,0.0)+coef
        targets[i]=par
    req=[0x30 if side=='x' else 0x20, 0x40, 0x80, 0x100]
    allw=set(range(9)); al=[allw]*4
    rng=random.Random(1); best=None
    for r in range(200):
        L=LayerLoader(targets, random.Random(rng.random()), w_setup=rng.uniform(0.1,3), w_d2=rng.uniform(0,1), noise=rng.choice([0.02,0.1,0.3]))
        d=L.run()
        if d is None: continue
        dd=gate_depth(L.gates)
        if best is None or dd<best[0]: best=(dd,L.gates)
    fx=fixup2(best[1],req,al,restarts=300,seed=3)
    return dict(side=side,fs=fs,cols=(1,2,4),cond=cond,targets=targets,gates=best[1],fix=fx[2],req=req,al=al,newcode=newcode,depth=fx[0])
if __name__=="__main__":
    side=sys.argv[1]; fs=[int(a) for a in sys.argv[2].split(',')]; kind=sys.argv[3]; order=tuple(int(c) for c in sys.argv[4]); out=sys.argv[5]
    D=makeD_code(side,fs,kind,order)
    print(side,fs,kind,order,{i:len(D['targets'][i]) for i in range(3)},"greedy+fix",D['depth'])
    pickle.dump(D,open(out,'wb'))
