"""Polish a loader recipe for the in-span ready vector (max, then sum)."""
import pickle, sys, os
from lbeval2 import sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile
from kgen import side_plan
src=sys.argv[1]; out=sys.argv[2]; lo,hi=int(sys.argv[3]),int(sys.argv[4]); iters=int(sys.argv[5])
mu=float(sys.argv[6]) if len(sys.argv)>6 else 0.05
T0=float(sys.argv[7]) if len(sys.argv)>7 else 0.6
D=pickle.load(open(src,'rb'))
init=[(g[1],g[2]) for g in D['gates'] if g[0][0]=='cx']
e0,_=profile(D['gates']); f0,W0,c0,r0=side_plan(D['gates'],e0,D,0)
print('start',src,'depth',D.get('depth'),'rdy',r0,'max',max(r0),'sum',sum(r0),flush=True)
best=(max(r0),sum(r0)); 
for s in range(lo,hi+1):
    d,pen,g=sa4(D,init,seed=s,iters=iters,T0=T0,T1=0.02,lam=4,mu=mu,tag='pr%d'%(s%89))
    chk=check_loader2(g,D['newcode'])
    if pen!=0 or chk['max_dev']>1e-9: print(' seed',s,'invalid',flush=True); continue
    D2=dict(D); D2['gates']=g; D2['fix']=[]; D2['depth']=gate_depth(g); D2['placed']=False
    e,_=profile(g); fx,W4,co,rdy=side_plan(g,e,D2,0)
    key=(max(rdy),sum(rdy))
    print(f'  seed {s} depth {d} rdy {rdy} max {max(rdy)} sum {sum(rdy)} fix {len(fx)}',flush=True)
    if key<best:
        best=key; pickle.dump(D2,open(out,'wb')); print('   -> saved',out,flush=True)
