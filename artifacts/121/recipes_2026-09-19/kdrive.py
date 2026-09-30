import pickle,sys,os
from kgen import run_beam, build_kg
from kdrv import assemble
planp,xp,yp,T,w,mu,s,out=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5]),float(sys.argv[6]),int(sys.argv[7]),sys.argv[8]
pl=pickle.load(open(planp,'rb'))
DX=pickle.load(open(xp,'rb')); DY=pickle.load(open(yp,'rb'))
rc=run_beam(pl,T,w,mu,s,out)
if rc==0:
    kg=build_kg(pl,out); q=out.replace('.txt','.qasm')
    print('OK',out,assemble(DX,DY,kg,q),flush=True)
    pickle.dump((pl,kg),open(q.replace('.qasm','.pkl'),'wb'))
else: print('no',out,flush=True)
