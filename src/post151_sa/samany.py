import pickle, sys, time, random
from sadrv import run_sa
from sim import check_loader2, symbolic_final
from depth import gate_depth
src=sys.argv[1]; tag=sys.argv[2]; n=int(sys.argv[3]); iters=int(sys.argv[4]); base=int(sys.argv[5])
D=pickle.load(open(src,'rb')); best=None; rng=random.Random(base)
for k in range(n):
    s=base+k; T0=rng.choice([0.5,0.8,1.0,1.3]); lam=rng.choice([3,4,6]); mu=rng.choice([0.0,0.05,0.1])
    d,pen,g,err=run_sa(D,seed=s,iters=iters,T0=T0,T1=0.02,lam=lam,mu=mu,tag=tag)
    if pen: continue
    rows=symbolic_final(g); ok=all(any(rows[w]==v for w in A) for v,A in zip(D['req'],D['al']))
    if not ok: continue
    if best is None or d<best[0]:
        chk=check_loader2(g,D['newcode'])
        if chk['max_dev']>1e-9: print("BAD",s); continue
        best=(d,g); D2=dict(D); D2['gates']=g; D2['fix']=[]; D2['depth']=d
        pickle.dump(D2,open(f"runs/{tag}_best.pkl","wb"))
        print("seed",s,"T0",T0,"lam",lam,"mu",mu,"-> depth",d,flush=True)
print("done best",best[0] if best else None)
