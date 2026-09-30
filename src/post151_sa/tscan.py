"""Given loader recipes (with gates), scan T downwards for kernel feasibility and assemble."""
import pickle, sys, os
from kgen import plan, run_beam, build_kg
from kdrv import assemble
xp,yp=sys.argv[1],sys.argv[2]
Thi,Tlo=int(sys.argv[3]),int(sys.argv[4])
Wb=int(sys.argv[5]); mu=float(sys.argv[6]); seeds=[int(s) for s in sys.argv[7].split(',')]
tag=sys.argv[8]
DX=pickle.load(open(xp,'rb')); DY=pickle.load(open(yp,'rb'))
planp=f'runs/plan_{tag}.pkl'
if os.path.exists(planp): pl=pickle.load(open(planp,'rb'))
else:
    pl=plan(DX,DY,helpers=int(os.environ.get('HELPERS','0'))); pickle.dump(pl,open(planp,'wb'))
print('plan W',pl[1],'rdy',pl[3],'unl',pl[4],'fix',len(pl[0]),'max',max(pl[3]),'sum',sum(pl[3]),flush=True)
best=None
for T in range(Thi,Tlo-1,-1):
    ok=False
    for sd in seeds:
        out=f"runs/ts_{tag}_{T}_{sd}.txt"
        rc=run_beam(pl,T,Wb,mu,sd,out)
        if rc==0:
            kg=build_kg(pl,out); q=out.replace('.txt','.qasm')
            d,cx=assemble(DX,DY,kg,q)
            print(f"{tag} T={T} seed {sd} OK assembled {d} {cx} {q}",flush=True)
            pickle.dump((pl,kg),open(q.replace('.qasm','.pkl'),'wb'))
            best=(d,cx,q); ok=True; break
    if not ok:
        print(f"{tag} T={T} infeasible",flush=True); break
print('BEST',best,flush=True)
