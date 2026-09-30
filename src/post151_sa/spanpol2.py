import pickle, sys, os
from lbeval import sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile
src,out,seed,iters,mu=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),float(sys.argv[5])
T0=float(sys.argv[6]) if len(sys.argv)>6 else 0.35
D=pickle.load(open(src,'rb')); init=[(g[1],g[2]) for g in D['gates'] if g[0][0]=='cx']
d,pen,g=sa4(D,init,seed=seed,iters=iters,T0=T0,T1=0.02,lam=4,mu=mu,tag='sp%s'%seed)
chk=check_loader2(g,D['newcode']); e,_=profile(g)
# in-span times
req=D['req']; span={}
for b in range(1,16):
    v=0
    for k in range(4):
        if b>>k&1: v^=req[k]
    span[v]=b
from sim import symbolic_final
rows=symbolic_final(g)
ins=sorted(e[w] for w in range(9) if rows[w] in span)
print(src.split('/')[-1],seed,'depth',d,'pen',pen,'dev %.0e'%chk['max_dev'],'prof',e,'inspan',ins[:6],flush=True)
if pen==0 and chk['max_dev']<1e-9 and len(ins)>=4:
    D2=dict(D); D2['gates']=g; D2['depth']=gate_depth(g); pickle.dump(D2,open(out,'wb'))
