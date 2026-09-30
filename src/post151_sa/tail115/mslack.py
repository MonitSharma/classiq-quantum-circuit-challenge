"""Min number of gates forced into the last layer at depth T (0 => depth T-1 feasible)."""
import sys, time, numpy as np, scipy.sparse as sp
sys.path.insert(0,'/work/classiq/src/post151_sa')
from scipy.optimize import milp, LinearConstraint, Bounds
from cdag import build, heads_tails
from postopt import parse_ops, fuse, depth
from smilp import reduce_edges
def solve(ops,TT,tlim=600,mode='slack'):
    Tg,succ,pred=build(ops); n=len(Tg); h,t=heads_tails(n,succ,pred)
    red=reduce_edges(n,succ)
    lo=[h[i] for i in range(n)]; hi=[TT-t[i]+1 for i in range(n)]
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
    slack={}
    for w in range(18):
        for s in range(1,TT+1):
            g=[i for i in onw[w] if lo[i]<=s<=hi[i]]
            if len(g)<=1: continue
            for i in g: rows.append(r); cols.append(idx[i,s]); vals.append(1)
            if mode=='slack': slack[w,s]=nv+len(slack); rows.append(r); cols.append(slack[w,s]); vals.append(-1)
            lb.append(-np.inf if mode=='slack' else 0); ub.append(1); r+=1
    for i in range(n):
        for j in red[i]:
            for s in range(lo[j],hi[j]+1):
                if s-1>=hi[i]: continue
                for u in range(lo[j],s+1): rows.append(r); cols.append(idx[j,u]); vals.append(1)
                for u in range(lo[i],min(s-1,hi[i])+1): rows.append(r); cols.append(idx[i,u]); vals.append(-1)
                lb.append(-np.inf); ub.append(0); r+=1
    NV=nv+len(slack)
    A=sp.csr_matrix((vals,(rows,cols)),shape=(r,NV))
    c=np.zeros(NV)
    if mode=='slack':
        for kk in slack.values(): c[kk]=1
    else:
        for (i,s),kk in idx.items():
            if s==TT: c[kk]=1
    res=milp(c=c,constraints=LinearConstraint(A,lb,ub),integrality=np.ones(NV),bounds=Bounds(0,np.r_[np.ones(nv),np.full(len(slack),3)]),options={'time_limit':tlim,'disp':False})
    if res.x is None: return None,None
    if mode=='slack':
        over=[(w,s_,int(round(res.x[kk]))) for (w,s_),kk in slack.items() if res.x[kk]>0.5]
        when={i:s_ for (i,s_),kk in idx.items() if res.x[kk]>0.5}
        det=[]
        for w,s_,v in over:
            det.append((w,s_,v,[(i,Tg[i][0] if isinstance(Tg[i][0],str) else Tg[i][0],Tg[i][1]) for i in onw[w] if when.get(i)==s_]))
        return res.fun,det
    last=[i for (i,s),kk in idx.items() if s==TT and res.x[kk]>0.5]
    return res.fun,[(i,Tg[i]) for i in last]
if __name__=='__main__':
    ops=fuse(parse_ops(sys.argv[1])); TT=int(sys.argv[2]); t0=time.time()
    f,det=solve(ops,TT)
    print('min total overbooking at T',TT,':',f,'%.1fs'%(time.time()-t0))
    for d in det: print(d)
