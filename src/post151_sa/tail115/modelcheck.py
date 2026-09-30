"""Check whether the kernel model's schedule is a valid layered schedule of the assembled circuit."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, os, numpy as np
import paireval as P
import ev116, kdrv
from build import loader_ops
def kernel_times(pl, beampath, svec, T):
    seq, W, ST, rdy, unl = pl
    L=open(beampath).read().split('\n'); d,tau0=map(int,L[0].split())
    Tset=set(ev116.KTERMS); rows=list(ST); done=set(); pend={}; body=[]
    for i in range(8):
        if rows[i] in Tset and rows[i] not in done: done.add(rows[i]); pend[i]=rows[i]
    for k in range(1,d+1):
        t=list(map(int,L[k].split())); layer=[(t[1+2*q],t[2+2*q]) for q in range(t[0])]
        tau=tau0+k; used={x for p in layer for x in p}
        for i in list(pend):
            if i not in used and tau>svec[i] and tau<=(T-unl[i]):
                pend.pop(i); body.append((tau,'1q',W[i]))
        for c,tt in layer: body.append((tau,'cx',W[c],W[tt]))
        for tt,v in [(tt,rows[tt]^rows[c]) for c,tt in layer]:
            rows[tt]=v
            if v in Tset and v not in done: done.add(v); pend[tt]=v
    for i,v in pend.items(): body.append((None,'1q',W[i]))
    return body
def loader_sched(D,off):
    g=D['gates']+[(('cx',),c,t) for c,t in D.get('fix',[])]
    NV=9; wt=[0]*NV; lu=[False]*NV; out=[]
    for x in g:
        if x[0][0]=='cx':
            c,t=x[1],x[2]; l=max(wt[c],wt[t])+1; wt[c]=wt[t]=l; lu[c]=lu[t]=False; out.append((l,'cx',c+off,t+off))
        else:
            w=x[1]
            if not lu[w]: wt[w]+=1; lu[w]=True
            out.append((wt[w],'1q',w+off,x[0][0]))
    return out
if __name__=='__main__':
    DX=P.load(sys.argv[1],0); DY=P.load(sys.argv[2],1); T=int(sys.argv[3]); beam=sys.argv[4]
    co=np.load(f'{ROOT}/artifacts/116/recipes/kernel_co.npy'); ev116.KTERMS=[int(m) for m in np.flatnonzero(abs(co)>1e-10) if m]
    pl,srdy=P.windows(DX,DY)
    if os.environ.get('STRICT'): hz=P.hz_times(DX,DY,pl[1]); srdy=[max(a,b) for a,b in zip(srdy,hz)]
    Lx=loader_sched(DX,0); Ly=loader_sched(DY,9)
    K=kernel_times(pl,beam,srdy,T)
    U=[(T+1-o[0],)+o[1:] for o in reversed(Lx+Ly)]
    allops=[('L',)+o for o in Lx+Ly]+[('K',)+o for o in K]+[('U',)+o for o in U]
    # per wire occupancy
    occ={}
    bad=0
    for o in allops:
        part,t=o[0],o[1]
        if t is None: print('unscheduled kernel rotation',o); bad+=1; continue
        ws=[o[3]] if o[2]=='1q' else [o[3],o[4]]
        for w in ws: occ.setdefault((w,t),[]).append(o)
    for (w,t),lst in sorted(occ.items()):
        if len(lst)>1:
            kinds=set(x[0] for x in lst)
            if len(lst)==2 and all(x[2]=='1q' for x in lst): tag='fusable-1q'
            else: tag='CONFLICT'
            if tag=='CONFLICT' or os.environ.get('ALL'): print(tag,'wire',w,'t',t,lst); bad+=(tag=='CONFLICT')
    # ordering: per wire, list order vs time
    seqw={}
    for o in allops:
        if o[1] is None: continue
        ws=[o[3]] if o[2]=='1q' else [o[3],o[4]]
        for w in ws: seqw.setdefault(w,[]).append(o)
    inv=0
    for w,lst in seqw.items():
        for a,b in zip(lst,lst[1:]):
            if b[1]<a[1]: inv+=1; print('ORDER wire',w,a,b) if inv<30 else None
    print('conflicts',bad,'order inversions',inv)
