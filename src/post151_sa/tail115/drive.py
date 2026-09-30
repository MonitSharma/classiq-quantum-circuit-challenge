import sys, os, json, time, numpy as np
sys.path.insert(0,'/work/k/tail')
from ktail import solve_tail
ST=[2,8,1,4,32,64,192,16]; RDY=[34,39,42,46,35,43,44,44]; SRDY=[26,37,42,43,28,40,42,44]; TAU0=26
def load_terms(inpath):
    L=open(inpath).read().split('\n'); P=int(L[0]); return list(map(int,L[1].split()))[:P]
def read_dump(path):
    L=open(path).read().strip().split('\n'); i=0; out=[]
    while i<len(L):
        a=L[i].split(); assert a[0]=='S'; d=int(a[1]); rows=list(map(int,a[2:10])); done=int(a[10]); pend=int(a[11]); i+=1
        moves=[]
        for k in range(d):
            t=list(map(int,L[i].split())); moves.append([(t[1+2*q],t[2+2*q]) for q in range(t[0])]); i+=1
        out.append(dict(d=d,rows=rows,done=done,pend=pend,moves=moves))
    return out
def remaining_terms(st,terms):
    rem=[terms[i] for i in range(len(terms)) if not (st['done']>>i)&1]
    for w in range(8):
        if (st['pend']>>w)&1: rem.append(st['rows'][w])
    return rem
if __name__=='__main__':
    T=int(sys.argv[1]); dump=sys.argv[2]; inp=sys.argv[3]; tmo=int(sys.argv[4]); lim=int(sys.argv[5]) if len(sys.argv)>5 else 10**9
    DDL=[T-r for r in RDY]; terms=load_terms(inp)
    sts=read_dump(dump)
    for j,st in enumerate(sts[:lim]):
        rem=remaining_terms(st,terms); t0=time.time()
        res=solve_tail(st['rows'],rem,TAU0+st['d'],ST,RDY,SRDY,DDL,None,timeout=tmo)
        tag='SAT' if res else ('UNSAT' if res is False else 'TIMEOUT')
        print(j,'d',st['d'],'rem',len(rem),tag,'%.1fs'%(time.time()-t0),flush=True)
        if res:
            json.dump(dict(state=j,d=st['d'],moves=st['moves'],tail=res,T=T),open(dump+'.sol%d.json'%j,'w'))
            if '--first' in sys.argv: break
