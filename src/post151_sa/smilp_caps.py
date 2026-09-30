"""Exact commutation-aware rescheduling: time-indexed MILP (scipy/HiGHS) for target depth T."""
import sys, time, numpy as np, scipy.sparse as sp
from scipy.optimize import milp, LinearConstraint, Bounds
sys.path.insert(0,'.')
from cdag import build, heads_tails
from postopt import parse_ops, fuse, depth, write
def reduce_edges(n,succ):
    reach=[0]*n; red=[[] for _ in range(n)]
    for i in reversed(range(n)):
        for j in sorted(succ[i]):
            if not (reach[i]>>j)&1: red[i].append(j); reach[i]|=(1<<j)|reach[j]
    return red
def solve(ops,TT,tlim=600,verbose=True,wire_caps=None):
    Tg,succ,pred=build(ops); n=len(Tg); h,t=heads_tails(n,succ,pred)
    red=reduce_edges(n,succ)
    lo=[h[i] for i in range(n)]; hi=[TT-t[i]+1 for i in range(n)]
    if wire_caps:
        for i in range(n): hi[i]=min(hi[i],*(wire_caps.get(w,TT) for w in Tg[i][1]))
        for i in reversed(range(n)):
            if succ[i]: hi[i]=min(hi[i],min(hi[j]-1 for j in succ[i]))
    if any(hi[i]<lo[i] for i in range(n)):
        if verbose: print('infeasible precedence/cap bounds',flush=True)
        return None
    idx={}; k=0
    for i in range(n):
        for s in range(lo[i],hi[i]+1): idx[i,s]=k; k+=1
    nv=k; rows=[]; cols=[]; vals=[]; lb=[]; ub=[]; r=0
    for i in range(n):
        for s in range(lo[i],hi[i]+1): rows.append(r); cols.append(idx[i,s]); vals.append(1)
        lb.append(1); ub.append(1); r+=1
    onw=[[] for _ in range(18)]
    for i in range(n):
        for w in Tg[i][1]: onw[w].append(i)
    for w in range(18):
        for s in range(1,TT+1):
            g=[i for i in onw[w] if lo[i]<=s<=hi[i]]
            if len(g)<=1: continue
            for i in g: rows.append(r); cols.append(idx[i,s]); vals.append(1)
            lb.append(0); ub.append(1); r+=1
    for i in range(n):
        for j in red[i]:
            # for s in window of j: sum_{u<=s} x[j,u] - sum_{u<=s-1} x[i,u] <= 0
            for s in range(lo[j],hi[j]+1):
                if s-1>=hi[i]: continue   # i surely done
                for u in range(lo[j],s+1): rows.append(r); cols.append(idx[j,u]); vals.append(1)
                for u in range(lo[i],min(s-1,hi[i])+1): rows.append(r); cols.append(idx[i,u]); vals.append(-1)
                lb.append(-np.inf); ub.append(0); r+=1
    A=sp.csr_matrix((vals,(rows,cols)),shape=(r,nv))
    if verbose: print('T',TT,'vars',nv,'rows',r,flush=True)
    t0=time.time()
    res=milp(c=np.zeros(nv),constraints=LinearConstraint(A,lb,ub),integrality=np.ones(nv),bounds=Bounds(0,1),
             options={'time_limit':tlim,'disp':False})
    if verbose: print('status',res.status,res.message,'%.1fs'%(time.time()-t0),flush=True)
    if res.x is None or res.status not in (0,): return None
    x=res.x; when=[None]*n
    for (i,s),kk in idx.items():
        if x[kk]>0.5: when[i]=s
    order=sorted(range(n),key=lambda i:(when[i],i))
    return [ops[i] for i in order]
if __name__=='__main__':
    ops=fuse(parse_ops(sys.argv[1])); TT=int(sys.argv[2])
    out=solve(ops,TT,tlim=float(sys.argv[4]) if len(sys.argv)>4 else 600)
    if out:
        f=fuse(out); print('scheduled depth',depth(f),'gates',len(f),'cx',sum(1 for o in f if o[0]=='cx'))
        write(f,sys.argv[3])
