"""SAT encoding of the kernel CX+rotation network with per-wire windows.  Usage:
   ksat.py enc  <pair.pkl|champ> T out.cnf [opts...]   -> writes cnf + meta pickle
   ksat.py dec  meta.pkl sol -> kernel gate list, assemble, MILP check"""
import sys, pickle, itertools, os, json
sys.path.insert(0,'.')
from kdrv import KTERMS, CO
class Enc:
    def __init__(s): s.n=0; s.cl=[]
    def var(s): s.n+=1; return s.n
    def add(s,*c): s.cl.append(c)
def encode(ST,RDY,DDL,SRDY,CRDY,terms,T,maxcx=None,rotwin=None,extra=None,fix=None):
    N=len(ST); E=Enc()
    t0=min(min(RDY),min(SRDY),min(CRDY)); t1=max(DDL)
    # allowed CX at tau
    def cx_ok(a,b,tau): return CRDY[a]<tau<=DDL[a] and RDY[b]<tau<=DDL[b]
    def rot_ok(w,tau): return SRDY[w]<tau<=DDL[w]
    X={}; R={}
    for i in range(N):
        R[i,t0]=[None]*8   # constants
    const={}
    def bitlit(i,tau,k):
        v=R[i,tau][k]
        return v
    # represent constant bits via fixed vars
    TRUE=E.var(); E.add(TRUE)
    for i in range(N):
        R[i,t0]=[TRUE if (ST[i]>>k)&1 else -TRUE for k in range(8)]
    for tau in range(t0+1,t1+1):
        for a in range(N):
            for b in range(N):
                if a!=b and cx_ok(a,b,tau): X[a,b,tau]=E.var()
        for b in range(N):
            inc=[a for a in range(N) if (a,b,tau) in X]
            if not inc: R[b,tau]=R[b,tau-1]; continue
            row=[]
            for k in range(8):
                ys=[]
                for a in inc:
                    ra=R[a,tau-1][k]; x=X[a,b,tau]
                    if ra==-TRUE: continue
                    if ra==TRUE: ys.append(x); continue
                    y=E.var(); E.add(-y,x); E.add(-y,ra); E.add(y,-x,-ra); ys.append(y)
                old=R[b,tau-1][k]
                if not ys: row.append(old); continue
                if len(ys)==1: inc_l=ys[0]
                else:
                    inc_l=E.var(); E.add(-inc_l,*ys)
                    for y in ys: E.add(inc_l,-y)
                nw=E.var()
                if old==TRUE: E.add(nw,inc_l); E.add(-nw,-inc_l)
                elif old==-TRUE: E.add(-nw,inc_l); E.add(nw,-inc_l)
                else:
                    E.add(-nw,old,inc_l); E.add(-nw,-old,-inc_l); E.add(nw,-old,inc_l); E.add(nw,old,-inc_l)
                row.append(nw)
            R[b,tau]=row
        # at most one CX per wire
        for w in range(N):
            inv=[v for (a,b,t),v in X.items() if t==tau and (a==w or b==w)]
            for u,v in itertools.combinations(inv,2): E.add(-u,-v)
    # home at deadline and beyond
    for i in range(N):
        for k in range(8):
            lit=R[i,DDL[i]][k]; want=(ST[i]>>k)&1
            if lit in (TRUE,-TRUE):
                if (lit==TRUE)!=bool(want): E.add(-TRUE)   # unsat
            else: E.add(lit if want else -lit)
    # rotations
    IDLE={}
    for w in range(N):
        for tau in range(t0+1,t1+1):
            if not rot_ok(w,tau): continue
            inv=[v for (a,b,t),v in X.items() if t==tau and (a==w or b==w)]
            if not inv: IDLE[w,tau]=TRUE; continue
            d=E.var(); IDLE[w,tau]=d
            for v in inv: E.add(-d,-v)
    F={}
    for p in terms:
        opts=[]
        for w in range(N):
            for tau in range(t0+1,t1+1):
                if (w,tau) not in IDLE: continue
                row=R[w,tau]
                # quick infeasibility check against constants
                okc=True
                for k in range(8):
                    if row[k] in (TRUE,-TRUE) and (row[k]==TRUE)!=bool((p>>k)&1): okc=False; break
                if not okc: continue
                f=E.var(); F[p,w,tau]=f; opts.append(f)
                if IDLE[w,tau]!=TRUE: E.add(-f,IDLE[w,tau])
                for k in range(8):
                    if row[k] in (TRUE,-TRUE): continue
                    E.add(-f,row[k] if (p>>k)&1 else -row[k])
        if not opts: E.add(-TRUE)
        E.add(*opts)
    if fix:
        for (a,b,t),v in X.items():
            if t in fix: E.add(v if (a,b) in fix[t] else -v)
        for t,lst in fix.items():
            for (a,b) in lst:
                if (a,b,t) not in X: E.add(-TRUE)
    if maxcx is not None:   # sequential counter AMK over X (optional)
        xs=list(X.values()); K=maxcx; n=len(xs)
        s=[[E.var() for _ in range(K)] for _ in range(n)]
        for i,x in enumerate(xs):
            E.add(-x,s[i][0])
            if i>0:
                for j in range(K): E.add(-s[i-1][j],s[i][j])
                for j in range(1,K): E.add(-x,-s[i-1][j-1],s[i][j])
                E.add(-x,-s[i-1][K-1])
    return E,X,F,(t0,t1)
if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='enc':
        P=json.load(open(sys.argv[2])); T=int(sys.argv[3]); out=sys.argv[4]
        opts=dict(a.split('=') for a in sys.argv[5:])
        ST=P['ST']; RDY=P['RDY']; UNL=P['UNL']; SV=P['SV']
        rel=list(map(int,opts['relax'].split(','))) if 'relax' in opts else [0]*8
        DDL=[T-u+r for u,r in zip(UNL,rel)]
        SRDY=SV if opts.get('pull','1')=='1' else RDY
        CRDY=SV if opts.get('ctrl','0')=='1' else RDY
        if 'srdy' in opts: SRDY=list(map(int,opts['srdy'].split(',')))
        mc=int(opts['maxcx']) if 'maxcx' in opts else None
        fix=None
        if 'fixfrom' in opts:
            L=open(opts['fixfrom']).read().split('\n'); d,tau0=map(int,L[0].split()); upto=int(opts['fixupto']); fix={}
            for k in range(1,d+1):
                tau=tau0+k
                if tau>upto: break
                t=list(map(int,L[k].split())); fix[tau]=[(t[1+2*q],t[2+2*q]) for q in range(t[0])]
        E,X,F,rng=encode(ST,RDY,DDL,SRDY,CRDY,KTERMS,T,maxcx=mc,fix=fix)
        with open(out,'w') as f:
            f.write(f"p cnf {E.n} {len(E.cl)}\n")
            for c in E.cl: f.write(' '.join(map(str,c))+' 0\n')
        pickle.dump({'X':X,'F':F,'rng':rng,'ST':ST,'RDY':RDY,'DDL':DDL,'SRDY':SRDY,'T':T,'pair':sys.argv[2]},open(out+'.meta','wb'))
        print('vars',E.n,'clauses',len(E.cl),'cx vars',len(X),'fire vars',len(F),'range',rng)

def decode(meta_path, sol_path, Ttarget=None, out_prefix=None):
    """SAT model -> kernel gate list (champion plan wires) -> assembled qasm -> cancellation -> exact MILP."""
    import ev116
    from postopt import parse_ops, fuse, depth, write
    from canc import simplify
    import smilp
    M=pickle.load(open(meta_path,'rb'))
    lits=list(map(int,open(sol_path).read().split())); tv=set(l for l in lits if l>0)
    X,F=M['X'],M['F']; t0,t1=M['rng']; W=ev116.pl[1]
    cx={}; rot={}
    for (a,b,t),v in X.items():
        if v in tv: cx.setdefault(t,[]).append((a,b))
    used=set()
    for (p,w,t),v in F.items():
        if v in tv and p not in used: used.add(p); rot.setdefault(t,[]).append((w,p))
    assert used==set(KTERMS), (len(used),)
    body=[]
    for t in range(t0+1,t1+1):
        for (w,p) in rot.get(t,[]): body.append(('R',W[w],2*CO[p]))
        for (a,b) in cx.get(t,[]): body.append(('C',W[a],W[b]))
    kg=[('S',list(range(18)))]+body
    prefix=out_prefix or sol_path.replace('.sol','')
    r=ev116.evaluate_kg(kg,prefix,Ttarget or M['T'])
    r['ncx']=sum(len(v) for v in cx.values())
    return r
if __name__=='__main__' and sys.argv[1]=='dec':
    print(decode(sys.argv[2],sys.argv[3],int(sys.argv[4]) if len(sys.argv)>4 else None))
