import sys, time, pickle, random
import numpy as np
from sched2 import LayerLoader
from depth import gate_depth
from fixup2 import fixup2
from sim import check_loader2
def randp(rng):
    return dict(w_setup=rng.uniform(0.1,3), w_d2=rng.uniform(0,1), noise=rng.choice([0.02,0.1,0.3,1.0]), w_dep=rng.choice([0.0,0.5,1.0,2.0]))
def ils(targets, req, al, seconds=300, seed=0, init_restarts=300, fix_restarts=150):
    rng=random.Random(seed); t0=time.time()
    def full_cost(gates):
        fx=fixup2(gates,req,al,restarts=fix_restarts,seed=rng.randrange(10**6))
        return (fx[0],fx[2]) if fx else (999,None)
    best=None
    for r in range(init_restarts):
        L=LayerLoader(targets, random.Random(rng.random()), **randp(rng)); d=L.run()
        if d is None: continue
        dd=gate_depth(L.gates)
        if best is None or dd<best[0]: best=(dd,L.gates)
    cost,fix=full_cost(best[1]); best=(cost,best[1],fix)
    print("init",cost,flush=True)
    # replay best to get snapshots: re-run is not deterministic, so record by replaying gates layer-wise is complex;
    # instead: keep a pool of runs with snapshots
    L=LayerLoader(targets, random.Random(1), **randp(rng))
    it=0
    elite=[]
    while time.time()-t0<seconds:
        it+=1
        # generate a fresh run with snapshots
        L=LayerLoader(targets, random.Random(rng.random()), **randp(rng)); d=L.run(record=True)
        if d is None: continue
        dd=gate_depth(L.gates)
        if dd>best[0]+2: continue
        snaps=L.snaps
        # local improvement from random cut points
        for k in range(20):
            cut=snaps[rng.randrange(len(snaps)//3, len(snaps))]
            L2=LayerLoader(targets, random.Random(rng.random()), **randp(rng)); d2=L2.run(start=cut)
            if d2 is None: continue
            dd2=gate_depth(L2.gates)
            if dd2<=best[0]:
                c2,fx2=full_cost(L2.gates)
                if c2<best[0]:
                    best=(c2,L2.gates,fx2); print("improved",c2,"(loader",dd2,") it",it,"t %.0f"%(time.time()-t0),flush=True)
        if dd<=best[0]:
            c,fx=full_cost(L.gates)
            if c<best[0]: best=(c,L.gates,fx); print("improved",c,"(loader",dd,") it",it,"t %.0f"%(time.time()-t0),flush=True)
    return best
if __name__=="__main__":
    src=sys.argv[1]; seconds=int(sys.argv[2]); seed=int(sys.argv[3])
    D=pickle.load(open(src,'rb'))
    b=ils(D['targets'],D['req'],D['al'],seconds=seconds,seed=seed)
    chk=check_loader2(b[1],D['newcode'])
    print("final",b[0],"dev",chk['max_dev'])
    D2=dict(D); D2['gates']=b[1]; D2['fix']=b[2]; D2['depth']=b[0]
    pickle.dump(D2,open(src.replace('.pkl',f'_ils{seed}.pkl'),'wb'))
