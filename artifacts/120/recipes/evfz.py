import pickle, sys, os, glob
from lbeval2 import load_beam, sa4
from sim import check_loader2
from depth import gate_depth
from kdrv import profile
from kgen import side_plan
best={}
for out in sys.argv[1:]:
    b=os.path.basename(out).replace('fz_','')
    parts=b.replace('.txt','').split('_')
    base=None
    for n in range(len(parts),1,-1):
        cand='_'.join(parts[:n])
        if os.path.exists(f'runs/{cand}.pkl'): base=cand; break
    if base is None: print(out,'no base'); continue
    try:
        D=pickle.load(open(f'runs/{base}.pkl','rb'))
        bd,seq=load_beam(out)
    except Exception as e:
        print(out,'ERR',e); continue
    d,pen,g=sa4(D,seq,tag='ef')
    chk=check_loader2(g,D['newcode'])
    if pen!=0 or chk['max_dev']>1e-9: print(out,'invalid'); continue
    D2=dict(D); D2['gates']=g; D2['fix']=[]; D2['depth']=gate_depth(g); D2['placed']=False
    e,_=profile(g); fx,W4,co,rdy=side_plan(g,e,D2,0)
    key=(max(rdy),sum(rdy))
    side=base.split('_')[1]
    print(f"{out} depth {D2['depth']} rdy {rdy} max {max(rdy)} sum {sum(rdy)} fix {len(fx)}",flush=True)
    if side not in best or key<best[side][0]:
        best[side]=(key,out); pickle.dump(D2,open(f'runs/bestfz_{side}.pkl','wb'))
print('BEST',best)
