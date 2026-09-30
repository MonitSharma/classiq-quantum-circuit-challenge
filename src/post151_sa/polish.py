import pickle, sys
from lbeval import sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile
src,out,seed,iters,mu=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),float(sys.argv[5])
D=pickle.load(open(src,'rb')); init=[(g[1],g[2]) for g in D['gates'] if g[0][0]=='cx']
d,pen,g=sa4(D,init,seed=seed,iters=iters,T0=0.35,T1=0.02,lam=4,mu=mu,tag='pol%s'%seed)
chk=check_loader2(g,D['newcode'])
e,_=profile(g)
print(src,seed,'depth',d,'pen',pen,'dev %.1e'%chk['max_dev'],'prof',e,'sum',sum(e),'cx',sum(1 for x in g if x[0][0]=='cx'),flush=True)
if pen==0 and chk['max_dev']<1e-9:
    D2=dict(D); D2['gates']=g; D2['depth']=gate_depth(g); pickle.dump(D2,open(out,'wb'))
