import pickle, sys, subprocess
from kdrv import full_gates, code_vectors, profile, KTERMS
from sim import symbolic_final
from fixup2 import fixup2
def fix_and_windows(DX,DY,seeds=range(20)):
    gx=full_gates(DX); gy=full_gates(DY)
    ex,lx=profile(gx); ey,ly=profile(gy); e=ex+ey
    rows=symbolic_final(gx)+[r<<9 for r in symbolic_final(gy)]
    cv=code_vectors(DX,DY); allw=set(range(9)); best=None
    for s in seeds:
        fx=fixup2(gx,DX['req'],[allw]*4,restarts=300,seed=100+s)[2]
        fy=fixup2(gy,DY['req'],[allw]*4,restarts=300,seed=200+s)[2]
        seq=list(fx)+[(c+9,t+9) for c,t in fy]
        wt=list(e); r=list(rows)
        for c,t in seq:
            tau=max(wt[c],wt[t])+1; wt[c]=wt[t]=tau; r[t]^=r[c]
        W=[]; used=set()
        for v in cv:
            cand=[w for w in range(18) if r[w]==v and w not in used]; W.append(cand[0]); used.add(cand[0])
        rdy=[wt[w] for w in W]
        other=max([2*wt[w] for w in range(18) if w not in W]+[0])
        key=(sorted(rdy,reverse=True),other)
        if best is None or key<best[0]: best=(key,seq,W,rdy,other)
    return best[1:]
if __name__=="__main__":
    xp,yp,T,W,mu,seed=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),float(sys.argv[5]),int(sys.argv[6])
    DX=pickle.load(open(xp,'rb')); DY=pickle.load(open(yp,'rb'))
    seq,Wires,rdy,other=fix_and_windows(DX,DY)
    print('wires',Wires,'ready',rdy,'other',other,flush=True)
    inp=[str(len(KTERMS)),' '.join(map(str,KTERMS))]+[f"{r} {T-r}" for r in rdy]
    out=f"runs/kbp_T{T}_{seed}.txt"
    p=subprocess.run(["./c/kbeamP8",str(W),"120",str(seed),str(mu),out,"3","0"],input="\n".join(inp)+"\n",capture_output=True,text=True)
    print(p.stderr.strip().split('\n')[-1])
    pickle.dump((seq,Wires,rdy),open(f"runs/kbp_T{T}_{seed}_fix.pkl","wb"))
