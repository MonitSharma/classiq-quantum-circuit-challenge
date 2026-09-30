# General-frame kernel pipeline: fix-up to code span, window beam (MODE 4), direct assembly
import pickle, sys, subprocess, itertools, os
from kdrv import full_gates, profile, KTERMS, CO, assemble
from sim import symbolic_final
from unl import unload_depths
def span_map(req):
    m={}
    for b in range(1,16):
        v=0
        for k in range(4):
            if b>>k&1: v^=req[k]
        m[v]=b
    return m
def side_plan(g,e,D,off,maxlen=2,fixseeds=6):
    rows=symbolic_final(g); sm=span_map(D['req']); n=9; best=None
    ops=[(c,t) for c in range(n) for t in range(n) if c!=t]
    for L in range(0,maxlen+1):
        for seq in itertools.product(ops,repeat=L):
            r=list(rows); t=list(e)
            for c,tt in seq:
                tau=max(t[c],t[tt])+1; t[c]=t[tt]=tau; r[tt]^=r[c]
            ins=sorted([(t[w],w) for w in range(n) if r[w] in sm])
            if len(ins)<4: continue
            ch=ins[:4]; key=(max(x[0] for x in ch),sum(x[0] for x in ch),L)
            if best is None or key<best[0]: best=(key,list(seq),[w for _,w in ch],[sm[r[w]] for _,w in ch],[x[0] for x in ch])
    if best is None:
        from fixup2 import fixup2
        for s in range(fixseeds):
            f=fixup2(g,D['req'],[set(range(9))]*4,restarts=300,seed=300+s)[2]
            r=list(rows); t=list(e)
            for c,tt in f:
                tau=max(t[c],t[tt])+1; t[c]=t[tt]=tau; r[tt]^=r[c]
            W=[]; used=set()
            for v in D['req']:
                w=[w for w in range(9) if r[w]==v and w not in used][0]; W.append(w); used.add(w)
            key=(max(t[w] for w in W),sum(t[w] for w in W),len(f))
            if best is None or key<best[0]: best=(key,list(f),W,[1,2,4,8],[t[w] for w in W])
    _,seq,W,coords,rdy=best
    return [(c+off,tt+off) for c,tt in seq],[w+off for w in W],coords,rdy
def plan(DX,DY,helpers=0):
    gx=full_gates(DX); gy=full_gates(DY); ex,_=profile(gx); ey,_=profile(gy)
    fx,Wx,cx,rx=side_plan(gx,ex,DX,0); fy,Wy,cy,ry=side_plan(gy,ey,DY,9)
    seq=fx+fy; W=Wy+Wx; ST=cy+[c<<4 for c in cx]; rdy=ry+rx
    if helpers:
        # pick unused wires with the earliest ready times whose rows are outside the code span
        rows=symbolic_final(gx)+[r<<9 for r in symbolic_final(gy)]
        e=ex+ey
        smx=span_map(DX['req']); smy=span_map(DY['req'])
        r=list(rows); t=list(e)
        for c,tt in seq:
            tau=max(t[c],t[tt])+1; t[c]=t[tt]=tau; r[tt]^=r[c]
        cand=[]
        for w in range(18):
            if w in W: continue
            row=r[w]
            inspan=(row in smx) if w<9 else ((row>>9) in smy)
            if inspan: continue
            cand.append((t[w],w))
        cand.sort()
        for k in range(min(helpers,len(cand))):
            tw=cand[k][1]; W=W+[tw]; ST=ST+[1<<(8+k)]; rdy=rdy+[cand[k][0]]
    return seq,W,ST,rdy,unload_depths(DX,DY,seq,W)
def run_beam(pl,T,Wb,mu,seed,out,binary=None):
    seq,W,ST,rdy,unl=pl
    if binary is None: binary='./c/kbeamP%d'%len(W)
    inp=[str(len(KTERMS)),' '.join(map(str,KTERMS))]+[f"{s} {r} {T-u}" for s,r,u in zip(ST,rdy,unl)]
    env=dict(os.environ); env['SINGLES_PENDING']='1'
    p=subprocess.run([binary,str(Wb),str(max(T-2*min(rdy),1)),str(seed),str(mu),out,"4","0"],input="\n".join(inp)+"\n",capture_output=True,text=True,env=env)
    return p.returncode
def build_kg(pl,beampath):
    seq,W,ST,rdy,unl=pl
    L=open(beampath).read().split('\n'); d,tau0=map(int,L[0].split())
    Tset=set(KTERMS); rows=list(ST); done=set(); pend={}
    kg=[('S',list(range(18)))]+[('C',c,t) for c,t in seq]
    for i in range(len(W)):
        if rows[i] in Tset and rows[i] not in done: done.add(rows[i]); pend[i]=rows[i]
    for k in range(1,d+1):
        t=list(map(int,L[k].split())); layer=[(t[1+2*q],t[2+2*q]) for q in range(t[0])]; tau=tau0+k
        used={x for p in layer for x in p}
        for i in list(pend):
            if i not in used and tau>rdy[i]: kg.append(('R',W[i],2*CO[pend.pop(i)]))
        for c,tt in layer:
            assert tt not in pend; kg.append(('C',W[c],W[tt]))
        new=[(tt,rows[tt]^rows[c]) for c,tt in layer]
        for tt,v in new:
            rows[tt]=v
            if v in Tset and v not in done: done.add(v); pend[tt]=v
    for i,v in pend.items(): kg.append(('R',W[i],2*CO[v]))
    assert done==Tset
    # permutation among positions (allowed only for ancilla wires)
    ANC={6,7,8,15,16,17}
    sig=list(range(18)); pi={w:w for w in range(18)}
    for i in range(len(W)):
        if rows[i]!=ST[i]:
            j=ST.index(rows[i]); assert W[i] in ANC and W[j] in ANC, ('bad perm',i,j)
            sig[W[i]]=W[j]; pi[W[j]]=W[i]
    assert sorted(rows)==sorted(ST)
    kg[0]=('S',sig)
    kg+=[('C',pi[c],pi[t]) for c,t in reversed(seq)]
    return kg
