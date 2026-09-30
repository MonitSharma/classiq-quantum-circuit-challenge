"""At target T, minimise the number of wire-capacity violations (two gates on one wire in one layer)."""
import sys, time, numpy as np, scipy.sparse as sp
from scipy.optimize import milp, LinearConstraint, Bounds
sys.path.insert(0,'.')
from cdag import build, heads_tails
from smilp import reduce_edges
from postopt import parse_ops, fuse
def run(ops,TT,tlim=100):
    Tg,succ,pred=build(ops); n=len(Tg); h,t=heads_tails(n,succ,pred); red=reduce_edges(n,succ)
    lo=[h[i] for i in range(n)]; hi=[TT-t[i]+1 for i in range(n)]
    idx={}; k=0
    for i in range(n):
        for s in range(lo[i],hi[i]+1): idx[i,s]=k; k+=1
    nx=k; vid={}
    rows=[]; cols=[]; vals=[]; lb=[]; ub=[]; r=0
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
            vid[w,s]=k; k+=1
            for i in g: rows.append(r); cols.append(idx[i,s]); vals.append(1)
            rows.append(r); cols.append(vid[w,s]); vals.append(-1)
            lb.append(-np.inf); ub.append(1); r+=1
    for i in range(n):
        for j in red[i]:
            for s in range(lo[j],hi[j]+1):
                if s-1>=hi[i]: continue
                for u in range(lo[j],s+1): rows.append(r); cols.append(idx[j,u]); vals.append(1)
                for u in range(lo[i],min(s-1,hi[i])+1): rows.append(r); cols.append(idx[i,u]); vals.append(-1)
                lb.append(-np.inf); ub.append(0); r+=1
    A=sp.csr_matrix((vals,(rows,cols)),shape=(r,k))
    c=np.zeros(k); c[nx:]=1
    ubv=np.ones(k); ubv[nx:]=3
    res=milp(c=c,constraints=LinearConstraint(A,lb,ub),integrality=np.ones(k),bounds=Bounds(0,ubv),options={'time_limit':tlim})
    print('T',TT,'status',res.status,'obj',res.fun, 'bound', getattr(res,'mip_dual_bound',None))
    if res.x is not None:
        v=[(w,s) for (w,s),kk in vid.items() if res.x[kk]>0.5]; print('violations at',v)
if __name__=='__main__':
    ops=fuse(parse_ops(sys.argv[1]))
    for TT in map(int,sys.argv[2].split(',')): run(ops,TT)
