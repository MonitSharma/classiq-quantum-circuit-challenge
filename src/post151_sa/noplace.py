import pickle, sys, random
from sadrv import run_sa
from sim import check_loader2
from depth import gate_depth
src=sys.argv[1]; out=sys.argv[2]; n=int(sys.argv[3]); iters=int(sys.argv[4])
D=pickle.load(open(src,'rb'))
D0=dict(D); D0['req']=[]; D0['al']=[]
init=[(g[1],g[2]) for g in D['gates'] if g[0][0]=='cx']
best=None
for k in range(n):
    d,pen,g,err=run_sa(D0,seed=300+k,iters=iters,T0=[0.5,0.8,1.2][k%3],T1=0.02,lam=4,mu=0.03,init=init,tag='np')
    if pen: continue
    chk=check_loader2(g,D['newcode'])
    print("seed",k,"depth",d,"dev %.1e"%chk['max_dev'],flush=True)
    if chk['max_dev']<1e-9 and (best is None or d<best):
        best=d; D2=dict(D); D2['gates']=g; D2['fix']=[]; D2['depth']=d; D2['placed']=False
        pickle.dump(D2,open(out,'wb')); init=[(x[1],x[2]) for x in g if x[0][0]=='cx']
