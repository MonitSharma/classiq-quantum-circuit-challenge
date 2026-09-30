"""Exact rescheduling MILP with commutation + free placement of multi-slot phase terms (+fusion into cores)."""
import sys, time, math, numpy as np, scipy.sparse as sp
from scipy.optimize import milp, LinearConstraint, Bounds
sys.path.insert(0,'.')
from canc import tag, com, simplify
from postopt import parse_ops, fuse, depth, write
def isdiag(U): return abs(U[0,1])+abs(U[1,0])<1e-12
def analyze(ops, nq=18):
    """returns per-op parity for diag gates, segments per wire in terms of op indices"""
    par=[1<<i for i in range(nq)]; nv=nq
    dpar={}; seg=[[{'par':par[w],'A':None,'B':None}] for w in range(nq)]
    for k,o in enumerate(ops):
        if o[0]=='cx':
            c,t=o[1]; seg[t][-1]['B']=k; par[t]^=par[c]; seg[t].append({'par':par[t],'A':k,'B':None})
        elif isdiag(o[2]): dpar[k]=par[o[1][0]]
        else:
            w=o[1][0]; seg[w][-1]['B']=k; par[w]=1<<nv; nv+=1; seg[w].append({'par':par[w],'A':k,'B':None})
    return dpar,seg
def solve(ops,TT,tlim=120,verbose=True,allow_fuse=True):
    n0=len(ops); dpar,seg=analyze(ops)
    where={}
    for w in range(18):
        for sg in seg[w]: where.setdefault(sg['par'],[]).append((w,sg['A'],sg['B']))
    cnt={}
    for k,p in dpar.items(): cnt[p]=cnt.get(p,0)+1
    assert all(v==1 for v in cnt.values()), 'run canc.simplify first (duplicate parities)'
    def fusable(opts):
        for (w,A,B) in opts:
            for X in (A,B):
                if X is not None and ops[X][0]!='cx' and not isdiag(ops[X][2]): return True
        return False
    multi={k:where[p] for k,p in dpar.items() if len(where[p])>1 or (allow_fuse and fusable(where[p]))}
    if verbose: print('multi-slot terms',len(multi),[len(v) for v in multi.values()],flush=True)
    fixed=[k for k in range(n0) if k not in multi]; fidx={k:i for i,k in enumerate(fixed)}
    F=[tag(ops[k]) for k in fixed]; n=len(F)
    succ=[set() for _ in range(n)]; pred=[set() for _ in range(n)]; last=[[] for _ in range(18)]
    for j in range(n):
        b=F[j]
        for w in b[1]:
            for i in reversed(last[w]):
                if i in pred[j]: continue
                if not com(F[i],b): succ[i].add(j); pred[j].add(i)
            last[w].append(j)
    # chain parity-changing events on wires that carry slot options
    slotw=set(w for opts in multi.values() for (w,A,B) in opts)
    for w in slotw:
        ev=[fidx[k] for k in fixed if (ops[k][0]=='cx' and ops[k][1][1]==w) or (ops[k][0]!='cx' and ops[k][1][0]==w and not isdiag(ops[k][2]))]
        for a,b in zip(ev,ev[1:]):
            if b not in succ[a]: succ[a].add(b); pred[b].add(a)
    order=list(range(n))  # original order is topological
    h=[1]*n
    for j in order:
        if pred[j]: h[j]=1+max(h[i] for i in pred[j])
    tl=[1]*n
    for i in reversed(order):
        if succ[i]: tl[i]=1+max(tl[j] for j in succ[i])
    reach=[0]*n; red=[[] for _ in range(n)]
    for i in reversed(range(n)):
        for j in sorted(succ[i]):
            if not (reach[i]>>j)&1: red[i].append(j); reach[i]|=(1<<j)|reach[j]
    lo=[h[i] for i in range(n)]; hi=[TT-tl[i]+1 for i in range(n)]
    if any(hi[i]<lo[i] for i in range(n)): return None
    idx={}; k=0
    for i in range(n):
        for s in range(lo[i],hi[i]+1): idx[i,s]=k; k+=1
    # slot options
    opt=[]  # (term op index, w, A(fixed idx or None), B, kind, s or None)
    for g,opts in multi.items():
        for (w,A,B) in opts:
            Af=fidx[A] if A is not None else None; Bf=fidx[B] if B is not None else None
            a_lo=lo[Af]+1 if Af is not None else 1; b_hi=hi[Bf]-1 if Bf is not None else TT
            for s in range(a_lo,b_hi+1): opt.append((g,w,Af,Bf,'s',s)); idx[('o',len(opt)-1)]=k; k+=1
            if allow_fuse:
                if Af is not None and ops[fixed[Af]][0]!='cx' and not isdiag(ops[fixed[Af]][2]):
                    opt.append((g,w,Af,Bf,'fA',None)); idx[('o',len(opt)-1)]=k; k+=1
                if Bf is not None and ops[fixed[Bf]][0]!='cx' and not isdiag(ops[fixed[Bf]][2]):
                    opt.append((g,w,Af,Bf,'fB',None)); idx[('o',len(opt)-1)]=k; k+=1
    nv=k; rows=[]; cols=[]; vals=[]; lb=[]; ub=[]; r=0
    def add(entries,l,u):
        nonlocal r
        for c,v in entries: rows.append(r); cols.append(c); vals.append(v)
        lb.append(l); ub.append(u); r+=1
    for i in range(n): add([(idx[i,s],1) for s in range(lo[i],hi[i]+1)],1,1)
    byterm={}
    for oi,o in enumerate(opt): byterm.setdefault(o[0],[]).append(oi)
    for g,ois in byterm.items(): add([(idx['o',oi],1) for oi in ois],1,1)
    onw=[[] for _ in range(18)]
    for i in range(n):
        for w in F[i][1]: onw[w].append(i)
    slot_on={}
    for oi,o in enumerate(opt):
        if o[4]=='s': slot_on.setdefault((o[1],o[5]),[]).append(oi)
    for w in range(18):
        for s in range(1,TT+1):
            e=[(idx[i,s],1) for i in onw[w] if lo[i]<=s<=hi[i]]+[(idx['o',oi],1) for oi in slot_on.get((w,s),[])]
            if len(e)>1: add(e,0,1)
    for i in range(n):
        for j in red[i]:
            for s in range(lo[j],hi[j]+1):
                if s-1>=hi[i]: continue
                add([(idx[j,u],1) for u in range(lo[j],s+1)]+[(idx[i,u],-1) for u in range(lo[i],min(s-1,hi[i])+1)],-np.inf,0)
    for oi,o in enumerate(opt):
        if o[4]!='s': continue
        g,w,Af,Bf,_,s=o; v=idx['o',oi]
        if Af is not None and s-1<hi[Af]:
            add([(v,1)]+[(idx[Af,u],-1) for u in range(lo[Af],min(s-1,hi[Af])+1)],-np.inf,0)
        if Bf is not None and s+1>lo[Bf]:
            add([(v,1)]+[(idx[Bf,u],-1) for u in range(max(s+1,lo[Bf]),hi[Bf]+1)],-np.inf,0)
    A=sp.csr_matrix((vals,(rows,cols)),shape=(r,nv))
    if verbose: print('T',TT,'vars',nv,'rows',r,flush=True)
    t0=time.time()
    res=milp(c=np.zeros(nv),constraints=LinearConstraint(A,lb,ub),integrality=np.ones(nv),bounds=Bounds(0,1),options={'time_limit':tlim})
    if verbose: print('status',res.status,'%.1fs'%(time.time()-t0),flush=True)
    if res.x is None or res.status!=0: return None
    x=res.x; when={}
    for (i,s),kk in [(key,v) for key,v in idx.items() if key[0]!='o']:
        if x[kk]>0.5: when[i]=s
    items=[(when[i],0,i,ops[fixed[i]]) for i in range(n)]
    newU={}
    for oi,o in enumerate(opt):
        if x[idx['o',oi]]>0.5:
            g,w,Af,Bf,kind,s=o; D=ops[g][2]
            if kind=='s': items.append((s,0,10**6+oi,('u3',(w,),D)))
            elif kind=='fA': newU[Af]=D@newU.get(Af,ops[fixed[Af]][2])
            else: newU[Bf]=newU.get(Bf,ops[fixed[Bf]][2])@D
    items=[(t,a,b,(o if b>=10**6 or b not in newU else ('u3',o[1],newU[b]))) for (t,a,b,o) in items]
    items.sort(key=lambda z:(z[0],z[2]))
    return [z[3] for z in items]
if __name__=='__main__':
    ops=fuse(simplify(fuse(parse_ops(sys.argv[1])),verbose=False))
    for TT in map(int,sys.argv[2].split(',')):
        out=solve(ops,TT,tlim=float(sys.argv[4]) if len(sys.argv)>4 else 120)
        if out:
            f=fuse(out); print('T',TT,'scheduled depth',depth(f),'gates',len(f),'cx',sum(1 for o in f if o[0]=='cx'))
            write(f,sys.argv[3].replace('.qasm',f'_{TT}.qasm')); break
