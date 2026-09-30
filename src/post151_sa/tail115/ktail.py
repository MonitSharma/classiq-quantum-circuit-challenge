"""Exact SAT completion of a kernel-beam state in the calibrated window model.
Model (MODE 4, untyped windows = kbeam_t3 with CS=XS=RDY, CD=XD=ZD=DDL):
  CX(c,t) at tau: RDY[c]<tau<=DDL[c] and RDY[t]<tau<=DDL[t]
  rotation on w at tau: w idle, SRDY[w]<tau<=DDL[w], row(w) at start of layer == term
  row(w) after layer DDL[w] must equal home ST[w]; each remaining term fired exactly once."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import itertools, subprocess, sys, os, time
KISSAT=KISSAT
N=8
class CNF:
    def __init__(s): s.n=0; s.cl=[]
    def var(s): s.n+=1; return s.n
    def add(s,c): s.cl.append(c)
    def amo(s,lits):
        if len(lits)<=6:
            for a,b in itertools.combinations(lits,2): s.add([-a,-b])
        else:  # sequential counter
            prev=None
            for i,x in enumerate(lits):
                if i==len(lits)-1:
                    if prev: s.add([-x,-prev])
                    break
                y=s.var(); s.add([-x,y])
                if prev: s.add([-prev,y]); s.add([-x,-prev])
                prev=y
    def solve(s,timeout,seed=0):
        txt="p cnf %d %d\n"%(s.n,len(s.cl))+"\n".join(" ".join(map(str,c))+" 0" for c in s.cl)+"\n"
        try: r=subprocess.run([KISSAT,"-q","--time=%d"%timeout,"--seed=%d"%seed],input=txt,capture_output=True,text=True,timeout=timeout+20)
        except subprocess.TimeoutExpired: return None
        if "s SATISFIABLE" not in r.stdout: return False if "UNSATISFIABLE" in r.stdout else None
        val=set()
        for line in r.stdout.split("\n"):
            if line.startswith("v "):
                for x in line[2:].split():
                    x=int(x)
                    if x>0: val.add(x)
        return val
def solve_tail(rows0, remaining, tau0, ST, RDY, SRDY, DDL, terms_mask, timeout=60, seed=0, extra_ddl=None, asap=True, clean=True, cnf_out=None):
    """rows0: rows at time tau0 (after layer tau0). remaining: list of term masks still to fire. Returns list of layers [(rots:[(w,mask)], cxs:[(c,t)])] for tau0+1..E."""
    E=max(DDL); L=E-tau0
    if L<=0: return None
    F=CNF()
    R=[[None]*N for _ in range(L+1)]
    for w in range(N): R[0][w]=[None]*8
    const={}  # represent rows as list of literals or python bools
    def lit_const(b): return True if b else False
    for w in range(N): R[0][w]=[bool((rows0[w]>>b)&1) for b in range(8)]
    X=[dict() for _ in range(L)]; Rot=[dict() for _ in range(L)]
    rem=list(remaining); tfire={q:[] for q in rem}
    def active(w,tau): return RDY[w]<tau<=DDL[w]
    def ractive(w,tau): return SRDY[w]<tau<=DDL[w]
    TRUE=F.var(); F.add([TRUE])
    def L_(x):
        if x is True: return TRUE
        if x is False: return -TRUE
        return x
    for k in range(L):
        tau=tau0+k+1
        for c in range(N):
            for t in range(N):
                if c!=t and active(c,tau) and active(t,tau): X[k][c,t]=F.var()
        for w in range(N):
            if ractive(w,tau):
                for q in rem:
                    # quick filter: row must possibly equal q; if row is constant and differs, skip
                    rw=R[k][w]
                    if all(isinstance(b,bool) for b in rw) and sum((1<<i) for i,b in enumerate(rw) if b)!=q: continue
                    v=F.var(); Rot[k][w,q]=v; tfire[q].append(v)
                    for b in range(8):
                        want=bool((q>>b)&1); rb=rw[b]
                        if isinstance(rb,bool):
                            if rb!=want: F.add([-v])
                        else: F.add([-v, rb if want else -rb])
        # one op per wire per layer
        for w in range(N):
            lits=[v for (c,t),v in X[k].items() if c==w or t==w]+[v for (ww,q),v in Rot[k].items() if ww==w]
            F.amo(lits)
        # row update
        for t in range(N):
            ins=[(c,v) for (c,tt),v in X[k].items() if tt==t]
            if not ins: R[k+1][t]=R[k][t]; continue
            newrow=[]
            for b in range(8):
                terms=[]
                for c,xv in ins:
                    rc=R[k][c][b]
                    if rc is False: continue
                    if rc is True: terms.append(xv); continue
                    a=F.var(); F.add([-a,xv]); F.add([-a,rc]); F.add([a,-xv,-rc]); terms.append(a)
                r0=R[k][t][b]
                if not terms: newrow.append(r0); continue
                s_=F.var()
                for a in terms: F.add([-a,s_])
                F.add([-s_]+terms)
                r1=F.var(); r0l=L_(r0)
                F.add([-r1,r0l,s_]); F.add([-r1,-r0l,-s_]); F.add([r1,-r0l,s_]); F.add([r1,r0l,-s_])
                newrow.append(r1)
            R[k+1][t]=newrow
    # ASAP canonical form: an op at layer k>0 needs one of its wires busy at layer k-1 (or be disallowed there)
    if asap:
        busy=[[None]*N for _ in range(L)]
        for k in range(L):
            for w in range(N):
                lits=[v for (c,t),v in X[k].items() if c==w or t==w]+[v for (ww,q),v in Rot[k].items() if ww==w]
                if not lits: busy[k][w]=None; continue
                b=F.var(); busy[k][w]=b
                for l in lits: F.add([-l,b])
                F.add([-b]+lits)
        for k in range(1,L):
            for (c,t),v in X[k].items():
                if (c,t) not in X[k-1]: continue
                cl=[-v]+[busy[k-1][w] for w in (c,t) if busy[k-1][w] is not None]
                F.add(cl)
            for (w,q),v in Rot[k].items():
                if (w,q) not in Rot[k-1]: continue
                cl=[-v]+([busy[k-1][w]] if busy[k-1][w] is not None else [])
                F.add(cl)
    # coordinate cleanliness: after wire j's deadline, no other row contains coordinate j
    if clean:
        # coordinate of row r in ST basis: solve via inverse map on bits
        import numpy as _np
        M=_np.array([[(ST[j]>>b)&1 for b in range(8)] for j in range(N)],dtype=int)  # rows: ST[j] as bit vector
        # find linear functionals f_j with f_j(ST[i]) = delta_ij : f_j is a bit mask over row bits
        fun=[]
        for j in range(N):
            found=None
            for m in range(1,256):
                if all((bin(m&ST[i]).count('1')&1)==(1 if i==j else 0) for i in range(N)): found=m; break
            fun.append(found)
        for j in range(N):
            kd=DDL[j]-tau0
            for k in range(max(kd,0),L+1):
                for w in range(N):
                    if w==j: continue
                    bits=[R[k][w][b] for b in range(8) if (fun[j]>>b)&1]
                    consts=[x for x in bits if isinstance(x,bool)]; vars_=[x for x in bits if not isinstance(x,bool)]
                    par=sum(1 for x in consts if x)&1
                    if not vars_:
                        if par: return False
                        continue
                    if len(vars_)==1: F.add([-vars_[0]] if par==0 else [vars_[0]]); continue
                    # XOR(vars_) == par : encode small xor via enumeration (len<=3 expected)
                    import itertools as _it
                    for assign in _it.product([0,1],repeat=len(vars_)):
                        if (sum(assign)&1)!=par:
                            F.add([-v if a else v for v,a in zip(vars_,assign)])
    # homes at deadlines
    for w in range(N):
        k=DDL[w]-tau0
        if k<0: continue
        if k>L: k=L
        for b in range(8):
            want=bool((ST[w]>>b)&1); rb=R[k][w][b]
            if isinstance(rb,bool):
                if rb!=want: return False
            else: F.add([rb if want else -rb])
    for q in rem:
        if not tfire[q]: return False
        F.add(tfire[q]); F.amo(tfire[q])
    if cnf_out:
        open(cnf_out,'w').write("p cnf %d %d\n"%(F.n,len(F.cl))+"\n".join(" ".join(map(str,c))+" 0" for c in F.cl)+"\n")
    val=F.solve(timeout,seed)
    if not val: return val
    out=[]
    for k in range(L):
        rots=[(w,q) for (w,q),v in Rot[k].items() if v in val]
        cxs=[(c,t) for (c,t),v in X[k].items() if v in val]
        out.append((rots,cxs))
    return out
