"""Lower bound for ANY kernel on a fixed loader pair: loader + mirror inverse exact (commutation MILP),
kernel abstracted as per-wire typed ops (controls, rotations, targets) with per-layer control/target count parity."""
import sys, time, pickle, numpy as np, scipy.sparse as sp
from scipy.optimize import milp, LinearConstraint, Bounds
sys.path.insert(0,'.')
from kdrv import full_gates, XW, YW, PHYS
from build import loader_ops, inverse_ops
from canc import tag, com, kind
from postopt import fuse
def conv(ops):
    return [('cx',(o[1],o[2]),None) if o[0]=='cx' else ('u3',(o[1],),o[2]) for o in ops]
def solve(DX,DY,W,TT,NCX,NROT=63,tlim=300,verbose=True,zlist=None):
    gx=full_gates(DX); gy=full_gates(DY)
    L=loader_ops(gx,XW)+loader_ops(gy,YW); I=inverse_ops(L)
    Lf=fuse(conv(L)); If=fuse(conv(I)); F=[tag(o) for o in Lf+If]; nL=len(Lf); n=len(F)
    code=[PHYS[w] for w in W]
    succ=[set() for _ in range(n)]; pred=[set() for _ in range(n)]; last=[[] for _ in range(18)]
    for j in range(n):
        b=F[j]
        for w in b[1]:
            for i in reversed(last[w]):
                if i in pred[j]: continue
                barrier = (w in code) and i<nL<=j
                if barrier or not com(F[i],b): succ[i].add(j); pred[j].add(i)
            last[w].append(j)
    h=[1]*n
    for j in range(n):
        if pred[j]: h[j]=1+max(h[i] for i in pred[j])
    tl=[1]*n
    for i in reversed(range(n)):
        if succ[i]: tl[i]=1+max(tl[j] for j in succ[i])
    reach=[0]*n; red=[[] for _ in range(n)]
    for i in reversed(range(n)):
        for j in sorted(succ[i]):
            if not (reach[i]>>j)&1: red[i].append(j); reach[i]|=(1<<j)|reach[j]
    lo=h[:]; hi=[TT-tl[i]+1 for i in range(n)]
    if any(hi[i]<lo[i] for i in range(n)): print('trivially infeasible'); return None
    idx={}; k=0
    for i in range(n):
        for s in range(lo[i],hi[i]+1): idx[i,s]=k; k+=1
    # classify gate relation to Z-type / X-type kernel ops on wire w
    def blocksZ(g,w):   # g does not commute with a Z-type op on w
        if g[0]=='cx': return g[1][1]==w
        return g[3]!='Z'
    def blocksX(g,w):
        if g[0]=='cx': return g[1][0]==w
        return g[3]!='X'
    zv={}
    for w in code:
        for s in range(1,TT+1):
            for t in 'CRX': zv[w,s,t]=k; k+=1
    nv=k; rows=[]; cols=[]; vals=[]; lb=[]; ub=[]; r=[0]
    def add(e,l,u):
        for c,v in e: rows.append(r[0]); cols.append(c); vals.append(v)
        lb.append(l); ub.append(u); r[0]+=1
    for i in range(n): add([(idx[i,s],1) for s in range(lo[i],hi[i]+1)],1,1)
    onw=[[] for _ in range(18)]
    for i in range(n):
        for w in F[i][1]: onw[w].append(i)
    for w in range(18):
        for s in range(1,TT+1):
            e=[(idx[i,s],1) for i in onw[w] if lo[i]<=s<=hi[i]]
            if w in code: e+=[(zv[w,s,t],1) for t in 'CRX']
            if len(e)>1: add(e,0,1)
    for i in range(n):
        for j in red[i]:
            for s in range(lo[j],hi[j]+1):
                if s-1>=hi[i]: continue
                add([(idx[j,u],1) for u in range(lo[j],s+1)]+[(idx[i,u],-1) for u in range(lo[i],min(s-1,hi[i])+1)],-np.inf,0)
    for w in code:
        for typ,blk in (('Z',blocksZ),('X',blocksX)):
            Lb=[i for i in onw[w] if i<nL and blk(F[i],w)]; Ib=[i for i in onw[w] if i>=nL and blk(F[i],w)]
            Lmax=[i for i in Lb if not any((reach[i]>>j)&1 for j in Lb)]
            Imin=[j for j in Ib if not any((reach[i]>>j)&1 for i in Ib)]
            ts='CR' if typ=='Z' else 'X'
            for s in range(1,TT+1):
                for t in ts:
                    v=zv[w,s,t]
                    for i in Lmax:
                        if s-1>=hi[i]: continue
                        if s-1<lo[i]: add([(v,1)],0,0); continue
                        add([(v,1)]+[(idx[i,u],-1) for u in range(lo[i],s)],-np.inf,0)
                    for j in Imin:
                        if s+1<=lo[j]: continue
                        if s+1>hi[j]: add([(v,1)],0,0); continue
                        add([(v,1)]+[(idx[j,u],-1) for u in range(s+1,hi[j]+1)],-np.inf,0)
    add([(zv[w,s,'X'],1) for w in code for s in range(1,TT+1)],NCX,NCX)
    add([(zv[w,s,'R'],1) for w in code for s in range(1,TT+1)],NROT,np.inf)
    for s in range(1,TT+1):
        add([(zv[w,s,'C'],1) for w in code]+[(zv[w,s,'X'],-1) for w in code],0,0)
    A=sp.csr_matrix((vals,(rows,cols)),shape=(r[0],nv))
    if verbose: print('T',TT,'NCX',NCX,'vars',nv,'rows',r[0],flush=True)
    t0=time.time()
    res=milp(c=np.zeros(nv),constraints=LinearConstraint(A,lb,ub),integrality=np.ones(nv),bounds=Bounds(0,1),options={'time_limit':tlim})
    print('status',res.status,res.message[:60],'%.1fs'%(time.time()-t0),flush=True)
    if res.x is not None and res.status==0:
        x=res.x
        for w in code:
            tr=''.join(('c' if x[zv[w,s,'C']]>.5 else 'r' if x[zv[w,s,'R']]>.5 else 'x' if x[zv[w,s,'X']]>.5 else '.') for s in range(1,TT+1))
            print(f'{w:2d}',tr)
    return res.status
if __name__=='__main__':
    DX,DY,pl=pickle.load(open('../../../champ117.pkl','rb'))
    TT=int(sys.argv[1]); NCX=int(sys.argv[2])
    solve(DX,DY,pl[1],TT,NCX,tlim=float(sys.argv[3]) if len(sys.argv)>3 else 100)
