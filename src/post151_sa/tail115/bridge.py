"""Middle-out kernel: K = P . B . Q^-1.  P and Q are forward beam prefixes (Q with PREDONE = done(P));
B is an exact SAT bridge from P's end rows to Q's end rows covering the remaining terms.
Symmetric window model (rotations [SRDY+1, T-SRDY], CX [rdy+1, T-rdy]) so Q reversed is valid."""
import sys, os, json, time, itertools
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from ktail import solve_tail
from drive import read_dump, load_terms, ST, RDY, SRDY, TAU0
N=8
def mat_inv(cols):
    # cols: list of 8 ints (bit vectors); return inverse map as function via Gaussian elimination
    # Build augmented rows: we want A with A*cols[i]=e_i ; represent matrix as list of row bitmasks
    n=8; M=[[ (cols[j]>>i)&1 for j in range(n)] for i in range(n)]  # M[i][j] = bit i of col j
    I=[[1 if i==j else 0 for j in range(n)] for i in range(n)]
    for c in range(n):
        p=next(r for r in range(c,n) if M[r][c])
        M[c],M[p]=M[p],M[c]; I[c],I[p]=I[p],I[c]
        for r in range(n):
            if r!=c and M[r][c]:
                M[r]=[a^b for a,b in zip(M[r],M[c])]; I[r]=[a^b for a,b in zip(I[r],I[c])]
    return I   # I = M^{-1}
def apply(Mat, v):   # Mat: list of rows (8x8), v bit vector -> bit vector
    out=0
    for i in range(8):
        s=0
        for j in range(8):
            if Mat[i][j] and (v>>j)&1: s^=1
        out|=s<<i
    return out
def basis_change(SQ):
    # A = M_ST * M_Q^{-1}
    Qi=mat_inv(SQ)
    MST=[[ (ST[j]>>i)&1 for j in range(8)] for i in range(8)]
    A=[[sum(MST[i][k]*Qi[k][j] for k in range(8))&1 for j in range(8)] for i in range(8)]
    return A
def fired_of(st,terms):
    pend=set(st['rows'][w] for w in range(8) if (st['pend']>>w)&1)
    done=set(terms[i] for i in range(len(terms)) if (st['done']>>i)&1)
    return done-pend, pend
def bridge(P,Q,terms,T,predone,tmo=60):
    fP,_=fired_of(P,terms); fQ,_=fired_of(Q,terms); fQ=fQ-set(predone)
    if fP & fQ: return 'CLASH',None
    rem=[t for t in terms if t not in fP and t not in fQ]
    tau_a=TAU0+P['d']; end=(T+1-TAU0)-1-Q['d']   # last bridge layer time
    L=end-tau_a
    if L<1: return 'SHORT',None
    A=basis_change(Q['rows'])
    rows0=[apply(A,r) for r in P['rows']]; remA=[apply(A,t) for t in rem]
    ddl=[end]*8; rdy=[0]*8; srdy=[0]*8
    res=solve_tail(rows0,remA,tau_a,ST,rdy,srdy,ddl,None,timeout=tmo,clean=False)
    return ('SAT' if res else ('UNSAT' if res is False else 'TO')), dict(rem=len(rem),L=L,res=res,A=A)
if __name__=='__main__':
    T=int(sys.argv[1]); pdump=sys.argv[2]; pidx=int(sys.argv[3]); qdump=sys.argv[4]; inp=sys.argv[5]; tmo=int(sys.argv[6]); lim=int(sys.argv[7])
    terms=load_terms(inp); P=read_dump(pdump)[pidx]; fP,pP=fired_of(P,terms); predone=sorted(fP|pP)
    Qs=read_dump(qdump)
    for j,Q in enumerate(Qs[:lim]):
        t0=time.time(); tag,info=bridge(P,Q,terms,T,predone,tmo)
        print(j,tag,'rem',info and info['rem'],'L',info and info['L'],'%.1fs'%(time.time()-t0),flush=True)
        if tag=='SAT':
            json.dump(dict(P=pidx,Q=j,res=info['res'],A=info['A']),open(qdump+f'.bridge{pidx}_{j}.json','w'))
