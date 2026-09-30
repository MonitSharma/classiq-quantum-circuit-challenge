"""Replay the first d layers of a kernel schedule, then solve the tail exactly at target T."""
import sys, json, time, numpy as np
sys.path.insert(0,'/work/k/tail')
from ktail import solve_tail
from drive import ST,RDY,SRDY,TAU0
def replay(moves, d, terms, Tm):
    rows=list(ST); fired=set(); pend={}
    Tset=set(terms)
    for i in range(8):
        if rows[i] in Tset and rows[i] not in fired and rows[i] not in pend.values(): pend[i]=rows[i]
    created=set(pend.values())
    for k in range(1,d+1):
        layer=moves[k-1]; tau=TAU0+k; used={x for p in layer for x in p}
        for i in list(pend):
            if i not in used and tau>SRDY[i] and tau<=Tm-RDY[i]: fired.add(pend.pop(i))
        for c,t in layer: assert t not in pend
        for t,v in [(t,rows[t]^rows[c]) for c,t in layer]:
            rows[t]=v
            if v in Tset and v not in created: created.add(v); pend[t]=v
    rem=[q for q in terms if q not in fired]
    return rows, rem, fired
def load_moves(path):
    L=open(path).read().strip().split('\n'); d,tau0=map(int,L[0].split()); assert tau0==TAU0
    mv=[]
    for k in range(1,d+1):
        t=list(map(int,L[k].split())); mv.append([(t[1+2*q],t[2+2*q]) for q in range(t[0])])
    return mv
if __name__=='__main__':
    kpath=sys.argv[1]; co=np.load(sys.argv[2]); T=int(sys.argv[3]); Tm=int(sys.argv[4]); ds=list(map(int,sys.argv[5].split(','))); tmo=int(sys.argv[6])
    terms=list(map(int,np.flatnonzero(abs(co)>1e-10))); terms=[t for t in terms if t!=0]
    mv=load_moves(kpath); DDL=[T-r for r in RDY]
    for d in ds:
        rows,rem,fired=replay(mv,d,terms,Tm); t0=time.time()
        res=solve_tail(rows,rem,TAU0+d,ST,RDY,SRDY,DDL,None,timeout=tmo)
        tag='SAT' if res else ('UNSAT' if res is False else 'TIMEOUT')
        print(kpath.split('/')[-1],'d',d,'rem',len(rem),tag,'%.1fs'%(time.time()-t0),flush=True)
        if res:
            json.dump(dict(kernel=kpath,d=d,moves=mv[:d],tail=res,T=T),open(kpath+'.T%d_d%d.sol.json'%(T,d),'w')); break
