import pickle, sys
from kgen import run_beam, build_kg, plan
from kdrv import assemble
xp,yp,planp,T,Wb,mu,seed=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5]),float(sys.argv[6]),int(sys.argv[7])
DX=pickle.load(open(xp,'rb')); DY=pickle.load(open(yp,'rb'))
import os
try: pl=pickle.load(open(planp,'rb'))
except FileNotFoundError:
    pl=plan(DX,DY,helpers=int(os.environ.get('HELPERS','0'))); pickle.dump(pl,open(planp,'wb'))
print('plan W',pl[1],'rdy',pl[3],'unl',pl[4],'fix',len(pl[0]),flush=True)
out=f"runs/kgT{T}_s{seed}.txt"
rc=run_beam(pl,T,Wb,mu,seed,out)
if rc==0:
    kg=build_kg(pl,out); q=out.replace('.txt','.qasm')
    print(planp,'T',T,'mu',mu,'assembled',assemble(DX,DY,kg,q),q,flush=True); pickle.dump((pl,kg),open(q.replace('.qasm','.pkl'),'wb'))
else: print(planp,'T',T,'mu',mu,'infeasible',flush=True)
