"""Port of post190_commuting_schedule (commutation-DAG rescheduling) + native u3 fusion, no qiskit."""
import re, math, random, sys, numpy as np
from build import u3m, to_u3, check_u3
def parse_ops(path):
    src=open(path).read()
    st=[s.strip() for s in re.sub(r"//[^\n]*","",src).split(";") if s.strip()]
    ops=[]
    for s in st[3:]:
        m=re.fullmatch(r"u3\s*\(([^,]+),([^,]+),([^,]+)\)\s+q\s*\[\s*(\d+)\s*\]",s)
        if m: ops.append(('u3',(int(m.group(4)),),u3m(*[float(eval(m.group(k).replace('pi','math.pi'))) for k in (1,2,3)]))); continue
        m=re.fullmatch(r"cx\s+q\s*\[\s*(\d+)\s*\]\s*,\s*q\s*\[\s*(\d+)\s*\]",s)
        ops.append(('cx',(int(m.group(1)),int(m.group(2))),None))
    return ops
X=np.array([[0,1],[1,0]])
def commute(a,b):
    if not set(a[1]).intersection(b[1]): return True
    if a[0]=='cx' and b[0]=='cx': return a[1][0]!=b[1][1] and b[1][0]!=a[1][1]
    if a[0]=='u3' and b[0]=='u3': return np.max(abs(a[2]@b[2]-b[2]@a[2]))<1e-12
    if a[0]=='u3': a,b=b,a
    u=b[2]
    if b[1][0]==a[1][0]: return abs(u[0,1])+abs(u[1,0])<1e-12
    return np.max(abs(u@X-X@u))<1e-12
def dag(ops):
    n=len(ops); seen=[[] for _ in range(18)]; succ=[set() for _ in range(n)]
    for j,op in enumerate(ops):
        cands=set(i for w in op[1] for i in seen[w])
        for i in cands:
            if not commute(ops[i],op): succ[i].add(j)
        for w in op[1]: seen[w].append(j)
    reach=[0]*n; red=[[] for _ in range(n)]
    for i in reversed(range(n)):
        for j in sorted(succ[i]):
            if not (reach[i]>>j)&1:
                red[i].append(j); reach[i]|=(1<<j)|reach[j]
    pred=[[] for _ in range(n)]
    for i,nx in enumerate(red):
        for j in nx: pred[j].append(i)
    return red,pred
def schedule(ops,succ,pred,seed):
    rng=random.Random(seed); n=len(ops)
    height=[1]*n; tails=np.zeros((n,18),int)
    for i in reversed(range(n)):
        if succ[i]:
            height[i]+=max(height[j] for j in succ[i]); tails[i]=tails[succ[i]].max(axis=0)
        tails[i,list(ops[i][1])]+=1
    counts=list(map(len,pred)); ready={i for i in range(n) if counts[i]==0}; layers=[]
    noise=[0,.3,1,2,4,8][seed%6]; weight=[0,.2,.5,1][(seed//6)%4]
    while ready:
        ranked=sorted(ready,key=lambda i:(height[i]+weight*tails[i].max()+noise*rng.random(),-i),reverse=True)
        used=set(); layer=[]
        for i in ranked:
            if used.isdisjoint(ops[i][1]): layer.append(i); used.update(ops[i][1])
        ready.difference_update(layer)
        for i in layer:
            for j in succ[i]:
                counts[j]-=1
                if counts[j]==0: ready.add(j)
        layers.append(layer)
    return [i for l in layers for i in l]
def fuse(ops):
    pend={}; out=[]
    def flush(w):
        if w in pend:
            U=pend.pop(w)
            if not (abs(U[0,1])<1e-12 and abs(U[1,0])<1e-12 and abs(U[1,1]/U[0,0]-1)<1e-12):
                out.append(('u3',(w,),U))
    for op in ops:
        if op[0]=='cx':
            flush(op[1][0]); flush(op[1][1]); out.append(op)
        else:
            w=op[1][0]; pend[w]=op[2] if w not in pend else op[2]@pend[w]
    for w in list(pend): flush(w)
    return out
def depth(ops):
    wt=[0]*18
    for op in ops:
        l=max(wt[w] for w in op[1])+1
        for w in op[1]: wt[w]=l
    return max(wt)
def write(ops,path):
    lines=['OPENQASM 2.0;','include "qelib1.inc";','qreg q[18];']
    for op in ops:
        if op[0]=='cx': lines.append(f"cx q[{op[1][0]}],q[{op[1][1]}];")
        else:
            par=to_u3(op[2]); assert check_u3(op[2],par)<1e-9
            lines.append(f"u3({par[0]!r},{par[1]!r},{par[2]!r}) q[{op[1][0]}];")
    open(path,'w').write("\n".join(lines)+"\n")
def resched(ops,trials=600,rounds=3,seed0=0,verbose=False):
    best=fuse(ops); bd=depth(best)
    for r in range(rounds):
        succ,pred=dag(best); improved=False
        for s in range(trials):
            order=schedule(best,succ,pred,seed0+s)
            cand=fuse([best[i] for i in order]); d=depth(cand)
            if d<bd:
                bd=d; nb=cand; improved=True
                if verbose: print(" round",r,"seed",s,"depth",d,flush=True)
        if not improved: break
        best=nb
    return best,bd
if __name__=="__main__":
    ops=parse_ops(sys.argv[1]); print("initial",depth(ops))
    best,bd=resched(ops,trials=int(sys.argv[3]) if len(sys.argv)>3 else 300,verbose=True)
    write(best,sys.argv[2]); print("final",bd,"cx",sum(1 for o in best if o[0]=='cx'))
