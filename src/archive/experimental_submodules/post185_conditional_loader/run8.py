import sys, time, pickle, random, os
os.makedirs('runs', exist_ok=True)
from codes import *
from condlp import atoms_for, sparse_rep
from sched2 import LayerLoader
from sim import check_loader2
from depth import gate_depth
from fixup2 import fixup2
import numpy as np
side=sys.argv[1]; restarts=int(sys.argv[2]); seed=int(sys.argv[3])
cols=tuple(int(c) for c in sys.argv[4].split(',')); kind=sys.argv[5]; order=tuple(int(c) for c in sys.argv[6])
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
# required vectors in new-frame variables: original L_i = XOR of new bits j where (inverse frame)
# new bit j = XOR_i in cols[j] of old L_i  -> solve old L_i as combination of new bits
import itertools
Minv={}
for i in range(3):
    for combo in range(1,8):
        v=0
        for j in range(3):
            if combo>>j&1: v^=cols[j]
        if v==(1<<i): Minv[i]=combo
req=[0x30 if side=='x' else 0x20]+[sum(1<<(6+j) for j in range(3) if Minv[i]>>j&1) for i in range(3)]
anc={6,7,8}; allw=set(range(9))
moved={'x':[False,False,True,True],'y':[False,True,True,True]}[side]   # 185 kernel constraints
al=[anc if m else allw for m in moved]
rng=random.Random(seed); pool=[]; t0=time.time(); bestd=999
for r in range(restarts):
    p=dict(w_setup=rng.uniform(0.1,3), w_d2=rng.uniform(0,1), noise=rng.choice([0.02,0.1,0.3,1.0]), w_dep=rng.choice([0.0,0.5,1.0,2.0]))
    L=LayerLoader(targets, random.Random(rng.random()), **p)
    d=L.run()
    if d is None: continue
    dd=gate_depth(L.gates)
    if dd<=bestd+2:
        bestd=min(bestd,dd); pool.append((dd,L.gates))
pool=[q for q in pool if q[0]<=bestd+2]
pool.sort(key=lambda q:q[0])
res=[]
for dd,g in pool[:60]:
    fx=fixup2(g,req,al,restarts=250,seed=7)
    if fx is None: continue
    res.append((fx[0],dd,g,fx[2]))
res.sort(key=lambda q:q[0])
b=res[0]
chk=check_loader2(b[2],newcode)
print(side,cols,kind,order,{i:len(targets[i]) for i in range(3)},"loader",bestd,"best with fixup",b[0],"(loader",b[1],")","dev %.1e"%chk['max_dev'],"pool",len(pool),"t %.0f"%(time.time()-t0),flush=True)
pickle.dump(dict(side=side,cols=cols,cond=cond,targets=targets,gates=b[2],fix=b[3],req=req,al=al,newcode=newcode,depth=b[0]),open(f"runs/r8_{side}_{sys.argv[4].replace(',','-')}_{kind}{sys.argv[6]}_{seed}.pkl","wb"))
