import pickle, sys
from kdrv import run_ksa, assemble
xp,yp,seed,iters,tag=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),sys.argv[5]
DX=pickle.load(open(xp,'rb')); DY=pickle.load(open(yp,'rb'))
tot,pen,kg,err=run_ksa(DX,DY,seed=seed,iters=iters,T0=0.6,lam=8,tag=tag)
init=[l for l in err.split('\n') if l.startswith('init')]
res=None
if pen==0:
    res=assemble(DX,DY,kg,f'runs/{tag}_{seed}.qasm'); pickle.dump(kg,open(f'runs/{tag}_{seed}_kernel.pkl','wb'))
print(tag,seed,init,'total',tot,'pen',pen,'assembled',res,flush=True)
