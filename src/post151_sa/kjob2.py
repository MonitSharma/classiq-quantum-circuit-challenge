import pickle, sys
from kdrv import run_ksa, assemble, full_gates, code_vectors
from sim import symbolic_final
from fixup2 import fixup2
def beam_kernel(path):
    L=open(path).read().split('\n'); d=int(L[0]); seq=[]
    for l in L[1:d+1]:
        t=list(map(int,l.split()))
        for q in range(t[0]): seq.append((t[1+2*q],t[2+2*q]))
    return seq
def init_beam(DX,DY,kpath,seed=21):
    gx=full_gates(DX); gy=full_gates(DY)
    allw=set(range(9))
    fx=fixup2(gx,DX['req'],[allw]*4,restarts=600,seed=seed)[2]
    fy=fixup2(gy,DY['req'],[allw]*4,restarts=600,seed=seed+1)[2]
    seq=list(fx)+[(c+9,t+9) for c,t in fy]
    rows=symbolic_final(gx)+[r<<9 for r in symbolic_final(gy)]
    r=list(rows)
    for c,t in seq: r[t]^=r[c]
    cv=code_vectors(DX,DY); W=[]; used=set()
    for v in cv:
        cand=[w for w in range(18) if r[w]==v and w not in used]; W.append(cand[0]); used.add(cand[0])
    kseq=[(W[c],W[t]) for c,t in beam_kernel(kpath)]
    full=seq+kseq+list(reversed(seq))
    rr=list(rows)
    for c,t in full: rr[t]^=rr[c]
    assert rr==rows
    return full
if __name__=="__main__":
    xp,yp,kp,seed,iters,tag=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5]),sys.argv[6]
    DX=pickle.load(open(xp,'rb')); DY=pickle.load(open(yp,'rb'))
    init=init_beam(DX,DY,kp,seed=20+seed)
    tot,pen,kg,err=run_ksa(DX,DY,seed=seed,iters=iters,T0=0.6,lam=8,tag=tag,init=init)
    ii=[l for l in err.split('\n') if l.startswith('init')]
    res=None
    if pen==0:
        res=assemble(DX,DY,kg,f'runs/{tag}_{seed}.qasm'); pickle.dump(kg,open(f'runs/{tag}_{seed}_kernel.pkl','wb'))
    print(tag,seed,ii,'total',tot,'pen',pen,'assembled',res,flush=True)
