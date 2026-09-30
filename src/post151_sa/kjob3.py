import pickle, sys
from kdrv import run_ksa, assemble, full_gates
from sim import symbolic_final
def beam_kernel(path):
    L=open(path).read().split('\n'); d=int(L[0].split()[0]); seq=[]
    for l in L[1:d+1]:
        t=list(map(int,l.split()))
        for q in range(t[0]): seq.append((t[1+2*q],t[2+2*q]))
    return seq
xp,yp,fix,kp,seed,iters,tag=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],int(sys.argv[5]),int(sys.argv[6]),sys.argv[7]
T0=float(sys.argv[8]) if len(sys.argv)>8 else 0.6
DX=pickle.load(open(xp,'rb')); DY=pickle.load(open(yp,'rb'))
seq,W,rdy=pickle.load(open(fix,"rb"))[:3]
init=list(seq)+[(W[c],W[t]) for c,t in beam_kernel(kp)]+list(reversed(seq))
rows=symbolic_final(full_gates(DX))+[r<<9 for r in symbolic_final(full_gates(DY))]
rr=list(rows)
for c,t in init: rr[t]^=rr[c]
assert rr==rows
tot,pen,kg,err=run_ksa(DX,DY,seed=seed,iters=iters,T0=T0,lam=8,tag=tag,init=init)
ii=[l for l in err.split('\n') if l.startswith('init')]
res=None
if pen==0:
    res=assemble(DX,DY,kg,f'runs/{tag}_{seed}.qasm'); pickle.dump(kg,open(f'runs/{tag}_{seed}_kernel.pkl','wb'))
print(tag,seed,ii,'total',tot,'pen',pen,'assembled',res,flush=True)
