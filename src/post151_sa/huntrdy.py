"""Run the loader beam on a variant/seed, then report the in-span ready vector."""
import sys, os, subprocess, pickle
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile
from kgen import side_plan
def run(base,seed,W,maxd,tag=None):
    lb=f'runs/{base}.lb'; out=f'runs/hr_{base}_{W}_{seed}.txt'
    if not os.path.exists(out):
        env=dict(os.environ); env.update(WREACH2='0.15',NP='18',WSPREAD='0.6',SPCAP='3')
        r=subprocess.run(['./c/lbeam3',str(W),'24',str(maxd),str(seed),'16','0.5',out,'0.02'],
                         stdin=open(lb),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env)
        if r.returncode!=0: return None
    D=pickle.load(open(f'runs/{base}.pkl','rb'))
    bd,seq=load_beam(out)
    d,pen,g=sa4(D,seq,tag='hr%d'%(seed%97))
    chk=check_loader2(g,D['newcode'])
    if pen!=0 or chk['max_dev']>1e-9: return None
    D2=dict(D); D2['gates']=g; D2['fix']=[]; D2['depth']=gate_depth(g); D2['placed']=False
    e,_=profile(g)
    fx,W4,coords,rdy=side_plan(g,e,D2,0)
    return bd,D2['depth'],rdy,len(fx),D2
if __name__=='__main__':
    base=sys.argv[1]; W=int(sys.argv[2]); maxd=int(sys.argv[3]); lo,hi=int(sys.argv[4]),int(sys.argv[5])
    for s in range(lo,hi+1):
        r=run(base,s,W,maxd)
        if r is None: print(f"{base} s={s} -> none",flush=True); continue
        bd,d,rdy,nf,D2=r
        print(f"{base} s={s} beam {bd} depth {d} rdy {rdy} max {max(rdy)} sum {sum(rdy)} fix {nf}",flush=True)
        pickle.dump(D2,open(f'runs/hrD_{base}_{W}_{s}.pkl','wb'))
