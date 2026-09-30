import pickle, sys, time
from kdrv import run_ksa, assemble
DX=pickle.load(open(sys.argv[1],'rb')); DY=pickle.load(open(sys.argv[2],'rb')); tag=sys.argv[3]
seeds=[int(s) for s in sys.argv[4].split(',')]; iters=int(sys.argv[5]); T0=float(sys.argv[6])
best=None; init=None
for s in seeds:
    t0=time.time()
    tot,pen,kg,err=run_ksa(DX,DY,seed=s,iters=iters,T0=T0,lam=8,init=init,tag=tag)
    print("seed",s,"total",tot,"pen",pen,"t %.0f"%(time.time()-t0),flush=True)
    if pen==0 and (best is None or tot<best[0]):
        best=(tot,kg); d,cx=assemble(DX,DY,kg,f"runs/{tag}_best.qasm"); print("  assembled",d,cx,flush=True)
        pickle.dump(kg,open(f"runs/{tag}_best_kernel.pkl","wb"))
        init=[(g[1],g[2]) for g in kg if g[0]=='C']
