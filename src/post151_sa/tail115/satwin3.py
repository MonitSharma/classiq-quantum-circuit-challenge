"""SAT large-neighbourhood search on layered conditional loaders (9 wires)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import subprocess, itertools, pickle, sys, os, time, random
NV=9; KISSAT=KISSAT
TB=[1<<(6+i) for i in range(3)]
def plist_of(D):
    pl=[(m,i,a) for i in range(3) for m,a in D['targets'][i].items()]
    return pl,{m:k for k,(m,i,a) in enumerate(pl)}
def layerize(gates):
    """returns list of layers; each layer: dict wire-> list of ops; ops: ('cx',c,t) stored under c and t, or ('rz',a) / ('h',)"""
    wt=[0]*NV; lu=[False]*NV; placed=[]
    for g in gates:
        if g[0][0]=='cx':
            c,t=g[1],g[2]; l=max(wt[c],wt[t])+1; wt[c]=wt[t]=l; lu[c]=lu[t]=False; placed.append((l,g))
        else:
            w=g[1]
            if not lu[w]: wt[w]+=1; lu[w]=True
            placed.append((wt[w],g))
    D=max(wt); layers=[[] for _ in range(D)]
    for l,g in placed: layers[l-1].append(g)
    return layers
def replay(layers, D, pidx, pl):
    """simulate layer by layer; returns per-layer start states (rows, closed, doneset) and per-layer op records with parity ids"""
    rows=[1<<w for w in range(NV)]; closed=set(); done=set(); states=[]; recs=[]
    for li,L in enumerate(layers):
        states.append((list(rows),set(closed),set(done)))
        rec=[]
        # single-qubit ops first (rot then h), then cx using start rows
        start=list(rows)
        for g in L:
            if g[0][0]=='rz':
                p=pidx[start[g[1]]]; rec.append(('R',g[1],p)); done.add(p)
        for g in L:
            if g[0][0]=='h':
                w=g[1]; r=start[w]
                if li==0:
                    rec.append(('O',w)); continue   # opening H (first layer)
                cand=[i for i in range(3) if (r>>(6+i))&1 and i not in closed]
                i=cand[0]; rec.append(('H',w,i)); closed.add(i); rows[w]=TB[i]
        for g in L:
            if g[0][0]=='cx':
                c,t=g[1],g[2]; rec.append(('C',c,t)); rows[t]^=start[c]
        recs.append(rec)
    states.append((list(rows),set(closed),set(done)))
    return states,recs
class CNF:
    def __init__(s): s.n=0; s.cl=[]
    def var(s): s.n+=1; return s.n
    def add(s,c): s.cl.append(c)
    def solve(s,timeout=60):
        txt="p cnf %d %d\n"%(s.n,len(s.cl))+"\n".join(" ".join(map(str,c))+" 0" for c in s.cl)+"\n"
        try:
            r=subprocess.run([KISSAT,"-q","--time=%d"%timeout]+os.environ.get("KOPTS","").split(),input=txt,capture_output=True,text=True,timeout=timeout+10)
        except subprocess.TimeoutExpired: return None
        if "s SATISFIABLE" not in r.stdout: return False if "UNSATISFIABLE" in r.stdout else None
        val=set()
        for line in r.stdout.split("\n"):
            if line.startswith("v "):
                for x in line[2:].split():
                    x=int(x)
                    if x>0: val.add(x)
        return val
def solve_window(pl, startS, endS, recs_window, Wn, final=False, req=None, al=None, timeout=60, idle_last=(), idle_k=1, notarget_last=None, close_by=None, max_cx=None, row_encoding='aux', exact_once=False, eager_rotations=False, sym=False, proj=None):
    if row_encoding not in ('aux', 'direct'):
        raise ValueError('row_encoding must be aux or direct')
    if eager_rotations and not exact_once:
        raise ValueError('eager_rotations requires exact_once')
    rows0,closed0,done0=startS; rows1,closed1,done1=endS
    # proj: bitmask of row bits kept (relaxation: rows projected onto these bits; CX acts exactly on the
    # projection; a rotation only needs the projected row to match; plus 'fresh': a wire must be CX-targeted
    # (or closed) between two rotations). UNSAT of the projected problem implies UNSAT of the full one.
    VB=[v for v in range(NV) if proj is None or (proj>>v)&1]
    if proj is not None and eager_rotations: raise ValueError('proj is incompatible with eager_rotations')
    Pw=sorted(done1-done0); Cw=sorted(closed1-closed0)
    pm=[pl[p][0] for p in Pw]; pt=[pl[p][1] for p in Pw]
    F=CNF(); T=lambda: None
    R=[[[F.var() for v in range(NV)] for w in range(NV)] for k in range(Wn+1)]
    X=[[[F.var() if c!=t else None for t in range(NV)] for c in range(NV)] for k in range(Wn)]
    Rot=[[[F.var() for q in range(len(Pw))] for w in range(NV)] for k in range(Wn)]
    Hc=[[[F.var() for i in Cw] for w in range(NV)] for k in range(Wn)]
    Cb=[[F.var() for i in Cw] for k in range(Wn+1)]   # closed before layer k
    def fix(lit,val): F.add([lit if val else -lit])
    for w in range(NV):
        for v in VB: fix(R[0][w][v], (rows0[w]>>v)&1)
    if not final:
        for w in range(NV):
            for v in VB: fix(R[Wn][w][v], (rows1[w]>>v)&1)
    for k in range(Wn):
        for w in range(NV):
            busy_cx=[X[k][w][t] for t in range(NV) if t!=w]+[X[k][c][w] for c in range(NV) if c!=w]
            ones=Rot[k][w]+Hc[k][w]
            # at most one cx involvement
            for a,b in itertools.combinations(busy_cx,2): F.add([-a,-b])
            for a in busy_cx:
                for b in ones: F.add([-a,-b])
            for a,b in itertools.combinations(Rot[k][w],2): F.add([-a,-b])
            for a,b in itertools.combinations(Hc[k][w],2): F.add([-a,-b])
        # row update
        for t in range(NV):
            hz=Hc[k][t]
            for v in VB:
                if row_encoding == 'direct':
                    # A matching has at most one incoming CX. Condition each
                    # XOR directly on that edge; otherwise retain the row bit.
                    # This is equivalent to the auxiliary AND/OR construction.
                    r0=R[k][t][v]; r1=R[k+1][t][v]
                    incoming=[X[k][c][t] for c in range(NV) if c!=t]
                    F.add(incoming+hz+[-r0,r1])
                    F.add(incoming+hz+[r0,-r1])
                    for c in range(NV):
                        if c==t: continue
                        rc=R[k][c][v]; edge=X[k][c][t]
                        for p,q,o in [(0,0,0),(0,1,1),(1,0,1),(1,1,0)]:
                            F.add([-edge, r0 if p==0 else -r0,
                                   rc if q==0 else -rc, r1 if o==1 else -r1])
                    for idx,i in enumerate(Cw):
                        F.add([-hz[idx], r1 if v==6+i else -r1])
                    continue
                # contributions
                terms=[]
                for c in range(NV):
                    if c==t: continue
                    a=F.var()   # a = X[k][c][t] & R[k][c][v]
                    F.add([-a,X[k][c][t]]); F.add([-a,R[k][c][v]]); F.add([a,-X[k][c][t],-R[k][c][v]])
                    terms.append(a)
                # s = OR terms (at most one X to t so OR == XOR)
                s_=F.var()
                for a in terms: F.add([-a,s_])
                F.add([-s_]+terms)
                # if no H: R1 = R0 xor s
                nh=[x for x in hz]
                r0=R[k][t][v]; r1=R[k+1][t][v]
                for (p,q,o) in [(0,0,0),(0,1,1),(1,0,1),(1,1,0)]:
                    cl=[r0 if p==0 else -r0, s_ if q==0 else -s_, r1 if o==1 else -r1]+nh
                    F.add(cl)
                # if H for target i: R1 = e_{6+i}
                for idx,i in enumerate(Cw):
                    F.add([-hz[idx], R[k+1][t][v] if v==6+i else -R[k+1][t][v]])
        # rotation implies row equals mask
        for w in range(NV):
            for q in range(len(Pw)):
                for v in VB:
                    F.add([-Rot[k][w][q], R[k][w][v] if (pm[q]>>v)&1 else -R[k][w][v]])
                i=pt[q]
                if i in Cw: F.add([-Rot[k][w][q], -Cb[k][Cw.index(i)]])      # before own closing
                for j in range(3):
                    if j!=i and (pm[q]>>(6+j))&1 and j not in closed0:
                        if j in Cw: F.add([-Rot[k][w][q], Cb[k][Cw.index(j)]])
                        else: F.add([-Rot[k][w][q]])   # conditioning target not closed in window -> impossible
            # closing conditions
            for idx,i in enumerate(Cw):
                h=Hc[k][w][idx]
                F.add([-h, R[k][w][6+i]])
                F.add([-h, -Cb[k][idx]])
                for u in range(NV):
                    if u!=w: F.add([-h, -R[k][u][6+i]])
                for j in range(3):
                    if j==i or j in closed0: continue
                    if j in Cw: F.add([-h, -R[k][w][6+j], Cb[k][Cw.index(j)]])
                    else: F.add([-h, -R[k][w][6+j]])
                # all own parities done before (rotation layer <= k allowed only if same layer rotation fused before H)
        for idx,i in enumerate(Cw):
            # Cb[k+1] <-> Cb[k] or any Hc[k][*][idx]
            hs=[Hc[k][w][idx] for w in range(NV)]
            F.add([-Cb[k][idx], Cb[k+1][idx]])
            for h in hs: F.add([-h, Cb[k+1][idx]])
            F.add([-Cb[k+1][idx], Cb[k][idx]]+hs)
    for idx,i in enumerate(Cw):
        F.add([-Cb[0][idx]]); F.add([Cb[Wn][idx]])
        if close_by and i in close_by and close_by[i]<=Wn: F.add([Cb[close_by[i]][idx]])
    for q in range(len(Pw)):
        occurrences=[Rot[k][w][q] for k in range(Wn) for w in range(NV)]
        F.add(occurrences)
        if exact_once:
            # Each specified phase is emitted once. The historical encoding
            # only required at least one occurrence and could decode duplicates.
            # Keep this optional to preserve the old search space for comparison.
            prefix=None
            for lit in occurrences:
                if prefix is not None: F.add([-prefix,-lit])
                nxt=F.var(); F.add([-lit,nxt])
                if prefix is not None: F.add([-prefix,nxt])
                prefix=nxt
    if eager_rotations:
        # Search a normal form that emits each phase at its first eligible idle
        # slot. This removes choices of *when* to emit a phase from a CX route.
        # Treat UNSAT with this optional restriction as a restricted result.
        for q,p in enumerate(Pw):
            done=[F.var() for k in range(Wn+1)]
            F.add([-done[0]])
            for k in range(Wn):
                slots=[Rot[k][w][q] for w in range(NV)]
                F.add([-done[k],done[k+1]])
                for slot in slots: F.add([-slot,done[k+1]])
                F.add([-done[k+1],done[k]]+slots)
                for w in range(NV):
                    clause=[done[k],Rot[k][w][q]]
                    clause += [-R[k][w][v] if (pm[q]>>v)&1 else R[k][w][v]
                               for v in range(NV)]
                    clause += [X[k][w][t] for t in range(NV) if t!=w]
                    clause += [X[k][c][w] for c in range(NV) if c!=w]
                    if pt[q] in Cw: clause.append(Cb[k][Cw.index(pt[q])])
                    for j in range(3):
                        if j!=pt[q] and (pm[q]>>(6+j))&1 and j not in closed0:
                            if j in Cw: clause.append(-Cb[k][Cw.index(j)])
                            else: break
                    else: F.add(clause)
    # own-target rotations must happen at or before closing layer: covered by -Cb[k] (closing at k sets Cb[k+1]); same-layer rot+H ok
    if final:
        # all targets closed at end already enforced via Cw (closed1 must be all); placement
        for r,(vec,A) in enumerate(zip(req,al)):
            F.add([F_eq for F_eq in []]) if False else None
            chs=[]
            for w in A:
                e=F.var(); chs.append(e)
                for v in VB: F.add([-e, R[Wn][w][v] if (vec>>v)&1 else -R[Wn][w][v]])
                nt_=(notarget_last or {}).get(r,0)
                if nt_:
                    for k in range(max(0,Wn-nt_),Wn):
                        for c in range(NV):
                            if c!=w: F.add([-e,-X[k][c][w]])
                        for q in Hc[k][w]: F.add([-e,-q])
                kk_=idle_last.get(r,0) if isinstance(idle_last,dict) else (idle_k if r in idle_last else 0)
                if kk_:
                    for k in range(max(0,Wn-kk_),Wn):
                        for t in range(NV):
                            if t!=w: F.add([-e,-X[k][w][t]]); F.add([-e,-X[k][t][w]])
                        for q in Rot[k][w]: F.add([-e,-q])
                        for q in Hc[k][w]: F.add([-e,-q])
            F.add(chs)
    if proj is not None:
        fr=[[F.var() for w in range(NV)] for k in range(Wn+1)]
        for w in range(NV): F.add([fr[0][w]])
        for k in range(Wn):
            for w in range(NV):
                tg=[X[k][c][w] for c in range(NV) if c!=w]+list(Hc[k][w])
                for r in Rot[k][w]: F.add([-r,fr[k][w]])
                # fr[k+1] <-> tg or (fr[k] and no rotation at k)
                for x in tg: F.add([-x,fr[k+1][w]])
                F.add([-fr[k+1][w]]+tg+[fr[k][w]])
                for r in Rot[k][w]: F.add([-fr[k+1][w]]+tg+[-r])
    if sym:
        # ASAP normal form (satisfiability-preserving): a CX whose two wires are both idle in the previous
        # layer, or a rotation whose wire is idle in the previous layer and whose conditioning targets are
        # already closed there, could move one layer earlier without changing any later state. Every
        # solution can be pushed into this form (sum of op layers strictly decreases), so forbidding the
        # movable ops keeps SAT/UNSAT. Also forbid CX(c,t) at k and k+1 (an identity pair).
        # Not valid with FREEK > 0 in tailcnf (the free layers forbid ops on the Lx0 wire).
        B=[[F.var() for w in range(NV)] for k in range(Wn)]
        for k in range(Wn):
            for w in range(NV):
                ops=[X[k][w][t] for t in range(NV) if t!=w]+[X[k][c][w] for c in range(NV) if c!=w]+Rot[k][w]+Hc[k][w]
                F.add([-B[k][w]]+ops)
                for o in ops: F.add([-o,B[k][w]])
        for k in range(1,Wn):
            for c in range(NV):
                for t in range(NV):
                    if c!=t:
                        F.add([-X[k][c][t],B[k-1][c],B[k-1][t]])
                        F.add([-X[k-1][c][t],-X[k][c][t]])
            for w in range(NV):
                for q in range(len(Pw)):
                    cl=[-Rot[k][w][q],B[k-1][w]]; ok=True
                    for j in range(3):
                        if j!=pt[q] and (pm[q]>>(6+j))&1 and j not in closed0:
                            if j in Cw: cl.append(-Cb[k-1][Cw.index(j)])
                            else: ok=False
                    if ok: F.add(cl)
    if max_cx is not None:
        xs=[X[k][c][t] for k in range(Wn) for c in range(NV) for t in range(NV) if c!=t]
        # sequential counter: at most max_cx true
        n=len(xs); K=max_cx
        if K<0: return False
        S=[[F.var() for j in range(K)] for i in range(n)]
        for i in range(n):
            x=xs[i]
            if K>0: F.add([-x,S[i][0]])
            if i>0:
                for j in range(K):
                    F.add([-S[i-1][j],S[i][j]])
                    if j>0: F.add([-x,-S[i-1][j-1],S[i][j]])
                if K>0: F.add([-x,-S[i-1][K-1]])
            if K==0: F.add([-x])
    val=F.solve(timeout)
    if not val: return val
    # decode layers
    out=[]
    for k in range(Wn):
        L=[]
        for w in range(NV):
            for q in range(len(Pw)):
                if Rot[k][w][q] in val: L.append(('R',w,Pw[q]))
        for w in range(NV):
            for idx,i in enumerate(Cw):
                if Hc[k][w][idx] in val: L.append(('H',w,i))
        for c in range(NV):
            for t in range(NV):
                if c!=t and X[k][c][t] in val: L.append(('C',c,t))
        out.append(L)
    return out
def recs_to_gates(recs, pl):
    g=[]
    for L in recs:
        for op in L:
            if op[0]=='O': g.append((('h',),op[1]))
        for op in L:
            if op[0]=='R': g.append((('rz',pl[op[2]][2]),op[1]))
        for op in L:
            if op[0]=='H': g.append((('h',),op[1]))
        for op in L:
            if op[0]=='C': g.append((('cx',),op[1],op[2]))
    return g
