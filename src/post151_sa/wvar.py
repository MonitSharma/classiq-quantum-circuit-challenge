import sys, pickle, numpy as np, itertools
from scipy.optimize import linprog
from condlp import atoms_for
from mkD import makeD
def sparse_w(target, A, keys, wfun, iters=12, eps=1e-3):
    K=A.shape[1]; base=np.array([wfun(k) for k in keys]); w=base.copy(); best=None
    for it in range(iters):
        r=linprog(np.concatenate([w,w]),A_eq=np.hstack([A,-A]),b_eq=target,bounds=(0,None),method='highs')
        a=r.x[:K]-r.x[K:]; sup=np.where(np.abs(a)>1e-7)[0]
        sol,*_=np.linalg.lstsq(A[:,sup],target,rcond=None)
        if np.max(np.abs(A[:,sup]@sol-target))<1e-9:
            cost=sum(base[k] for k in sup)
            if best is None or cost<best[0]: best=(cost,sup,sol)
        w=base/(np.abs(a)+eps)
    return best[1],best[2]
if __name__=="__main__":
    D=pickle.load(open(sys.argv[1],'rb')); wts=[float(x) for x in sys.argv[2].split(',')]; out=sys.argv[3]
    # wts: weight per conditioning target index j (applied multiplicatively for atoms containing j)
    from codes import bits, xcode, ycode
    code=xcode if D['side']=='x' else ycode; B=bits(code)
    cols=D['cols']; Bn=np.array([sum(B[i] for i in range(3) if cols[j]>>i&1)%2 for j in range(3)])
    targets={}
    for i in range(3):
        keys,A=atoms_for(Bn,D['cond'][i])
        wf=lambda k: float(np.prod([wts[j] for j in k[1]])) if k[1] else 1.0
        sup,sol=sparse_w(np.pi*Bn[i].astype(float),A,keys,wf)
        par={}
        for k,coef in zip(sup,sol):
            s,sub=keys[k]; mask=(1<<(6+i))|s
            for j in sub: mask|=1<<(6+j)
            par[mask]=par.get(mask,0.0)+coef
        targets[i]=par
        pat={}
        for m in par:
            key=tuple(j for j in range(3) if j!=i and m>>(6+j)&1); pat[key]=pat.get(key,0)+1
        print("target",i,len(par),pat)
    D2=dict(D); D2['targets']=targets
    # regenerate greedy init
    import random
    from sched2 import LayerLoader
    from depth import gate_depth
    from fixup2 import fixup2
    rng=random.Random(1); best=None
    for r in range(200):
        L=LayerLoader(targets, random.Random(rng.random()), w_setup=rng.uniform(0.1,3), w_d2=rng.uniform(0,1), noise=rng.choice([0.02,0.1,0.3]))
        d=L.run()
        if d is None: continue
        dd=gate_depth(L.gates)
        if best is None or dd<best[0]: best=(dd,L.gates)
    fx=fixup2(best[1],D['req'],D['al'],restarts=300,seed=3)
    D2['gates']=best[1]; D2['fix']=fx[2]; D2['depth']=fx[0]
    print("greedy+fix",fx[0]); pickle.dump(D2,open(out,'wb'))
