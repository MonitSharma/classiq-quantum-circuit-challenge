import json, math, pickle, subprocess, sys, os, numpy as np
ROOT=os.environ.get('CLASSIQ_ROOT','.')
from sim import symbolic_final
from qa import parse, layers
from build import loader_ops, inverse_ops, emit, u3m
from kperm import kernel_action
XW=[0,1,2,3,4,5,15,16,17]; YW=[6,7,8,9,10,11,12,13,14]
PHYS=XW+YW
CO=np.round(np.array(json.load(open(os.path.join(ROOT,'artifacts/193/kernel_recipe.json')))['co'],float)*32)/32*math.pi
KTERMS=[m for m in range(1,256) if abs(CO[m])>1e-10]
def profile(gates):
    wt=[0]*9; lu=[False]*9
    for g in gates:
        if g[0][0]=='cx':
            c,t=g[1],g[2]; tm=max(wt[c],wt[t])+1; wt[c]=wt[t]=tm; lu[c]=lu[t]=False
        else:
            w=g[1]
            if not lu[w]: wt[w]+=1; lu[w]=True
    return wt,lu
def full_gates(D):
    return D['gates']+[(('cx',),c,t) for c,t in D.get('fix',[])]
def code_vectors(DX,DY):
    y=[v<<9 for v in DY['req']]; x=list(DX['req'])
    return y+x     # order py,Ly0,Ly1,Ly2,px,Lx0,Lx1,Lx2
def kmask_to_vec(m,cv):
    v=0
    for k in range(8):
        if m>>k&1: v^=cv[k]
    return v
def init_from_185(DX,DY,rowsX,rowsY):
    """sequence: kernel 185 CX mapped to wires currently holding code vectors (must already be placed), then swap undo"""
    rows=rowsX+[r<<9 for r in rowsY]
    cv=code_vectors(DX,DY)
    W=[]
    used=set()
    for k,v in enumerate(cv):
        cand=[w for w in range(18) if rows[w]==v and w not in used]
        W.append(cand[0]); used.add(cand[0])
    n,kg=parse(os.path.join(ROOT,'artifacts/185/kernel.qasm'))
    seq=[(W[g[1][0]],W[g[1][1]]) for g in kg if g[0]=='cx']
    res=kernel_action(os.path.join(ROOT,'artifacts/185/kernel.qasm')); perm={}
    for j in range(8):
        for i in range(8):
            if all(((res[b][0]>>j)&1)==((b>>i)&1) for b in range(256)): perm[j]=i
    # simulate rows to find current holder of each code vector, then swap back
    r=list(rows)
    for c,t in seq: r[t]^=r[c]
    for k in range(8):
        target=W[k]
        if r[target]==cv[k]: continue
        src=[w for w in range(18) if r[w]==cv[k]][0]
        for c,t in [(src,target),(target,src),(src,target)]:
            seq.append((c,t)); r[t]^=r[c]
    assert r==rows, "init does not restore"
    return seq
def init_with_fixups(DX,DY,rowsX,rowsY):
    from fixup2 import fixup2
    gx=full_gates(DX); gy=full_gates(DY)
    allw=set(range(9))
    fx=fixup2(gx,DX['req'],[allw]*4,restarts=400,seed=11)[2]
    fy=fixup2(gy,DY['req'],[allw]*4,restarts=400,seed=12)[2]
    seq=list(fx)+[(c+9,t+9) for c,t in fy]
    rows=rowsX+[r<<9 for r in rowsY]
    r=list(rows)
    for c,t in seq: r[t]^=r[c]
    cv=code_vectors(DX,DY)
    W=[]; used=set()
    for k,v in enumerate(cv):
        cand=[w for w in range(18) if r[w]==v and w not in used]; W.append(cand[0]); used.add(cand[0])
    n,kg=parse(os.path.join(ROOT,'artifacts/185/kernel.qasm'))
    kseq=[(W[g[1][0]],W[g[1][1]]) for g in kg if g[0]=='cx']
    r2=list(r)
    for c,t in kseq: r2[t]^=r2[c]
    for k in range(8):
        target=W[k]
        if r2[target]==cv[k]: continue
        src=[w for w in range(18) if r2[w]==cv[k]][0]
        for c,t in [(src,target),(target,src),(src,target)]:
            kseq.append((c,t)); r2[t]^=r2[c]
    assert r2==r
    rev=[(t_c[0],t_c[1]) for t_c in reversed(seq)]
    full=seq+kseq+rev
    rr=list(rows)
    for c,t in full: rr[t]^=rr[c]
    assert rr==rows
    return full
def init_with_anc_fixups(DX,DY,rowsX,rowsY):
    from fixup2 import fixup2
    gx=full_gates(DX); gy=full_gates(DY)
    anc={6,7,8}; allw=set(range(9))
    alx=[allw,allw,anc,anc]; aly=[allw,anc,anc,anc]
    fx=fixup2(gx,DX['req'],alx,restarts=600,seed=21)[2]
    fy=fixup2(gy,DY['req'],aly,restarts=600,seed=22)[2]
    seq=list(fx)+[(c+9,t+9) for c,t in fy]
    rows=rowsX+[r<<9 for r in rowsY]
    r=list(rows)
    for c,t in seq: r[t]^=r[c]
    cv=code_vectors(DX,DY)
    W=[]; used=set()
    for k,v in enumerate(cv):
        cand=[w for w in range(18) if r[w]==v and w not in used]; W.append(cand[0]); used.add(cand[0])
    n,kg=parse(os.path.join(ROOT,'artifacts/185/kernel.qasm'))
    kseq=[(W[g[1][0]],W[g[1][1]]) for g in kg if g[0]=='cx']
    res=kernel_action(os.path.join(ROOT,'artifacts/185/kernel.qasm')); perm={}
    for j in range(8):
        for i in range(8):
            if all(((res[b][0]>>j)&1)==((b>>i)&1) for b in range(256)): perm[j]=i
    pi={w:w for w in range(18)}
    for j,i in perm.items(): pi[W[i]]=W[j]
    rev=[(pi[c],pi[t]) for c,t in reversed(seq)]
    full=seq+kseq+rev
    return full
def run_ksa(DX,DY,seed=1,iters=10000000,T0=1.0,T1=0.02,lam=3.0,init=None,tag='ksa'):
    gx=full_gates(DX); gy=full_gates(DY)
    rowsX=symbolic_final(gx); rowsY=symbolic_final(gy)
    ex,lx=profile(gx); ey,ly=profile(gy)
    cv=code_vectors(DX,DY)
    vecs=[kmask_to_vec(m,cv) for m in KTERMS]
    if init is None:
        init=init_from_185(DX,DY,rowsX,rowsY) if DX.get('placed',True) and DY.get('placed',True) else init_with_anc_fixups(DX,DY,rowsX,rowsY)
    rows=rowsX+[r<<9 for r in rowsY]; e=ex+ey; lu=lx+ly
    ANC=sum(1<<w for w in (6,7,8,15,16,17))
    lines=[f"18 {len(vecs)} {ANC}"]+[str(v) for v in vecs]+[f"{rows[w]} {e[w]} {int(lu[w])}" for w in range(18)]+[str(len(init))]+[f"{c} {t}" for c,t in init]
    out=f"runs/{tag}_{seed}.txt"
    r=subprocess.run([os.environ.get("KSA_BIN","./c/ksa"),str(seed),str(iters),str(T0),str(T1),str(lam),out],input="\n".join(lines)+"\n",capture_output=True,text=True)
    txt=open(out).read().split("\n"); tot,pen,L=map(int,txt[0].split())
    sigma=list(map(int,txt[1].split()))
    kg=[('S',sigma)]
    for line in txt[2:]:
        if not line: continue
        t=line.split()
        if t[0]=='R': kg.append(('R',int(t[1]),2*CO[KTERMS[int(t[2])]]))
        else: kg.append(('C',int(t[1]),int(t[2])))
    return tot,pen,kg,r.stderr
def assemble(DX,DY,kg,out):
    gx=full_gates(DX); gy=full_gates(DY)
    Lops=loader_ops(gx,XW)+loader_ops(gy,YW)
    Kops=[]; remap={w:w for w in range(18)}
    for g in kg:
        if g[0]=='S':
            for w,u in enumerate(g[1]): remap[PHYS[u]]=PHYS[w]
            continue
        if g[0]=='C': Kops.append(('cx',PHYS[g[1]],PHYS[g[2]]))
        else: Kops.append(('1q',PHYS[g[1]],np.diag([1,np.exp(1j*g[2])])))
    inv=[]
    for o in inverse_ops(Lops):
        inv.append(('cx',remap[o[1]],remap[o[2]]) if o[0]=='cx' else ('1q',remap[o[1]],o[2]))
    ops=Lops+Kops+inv
    if os.environ.get('PULL_KERNEL_RZ'):
        # Only pull kernel phase gadgets left.  Pulling loader phases too can
        # worsen the loader's own critical path even though the commutation is
        # algebraically valid.  A kernel Z phase commutes through every CX
        # for which its wire is the control, including loader CXs.
        lo=len(Lops); hi=lo+len(Kops)
        for i in range(hi-1,lo-1,-1):
            g=ops[i]
            if g[0]!='1q' or abs(g[2][0,1])>1e-10 or abs(g[2][1,0])>1e-10: continue
            j=i
            while j>0 and ops[j-1][0]=='cx' and ops[j-1][1]==g[1]:
                ops[j-1],ops[j]=ops[j],ops[j-1]; j-=1
    open(out,'w').write(emit(ops))
    n,gg=parse(out); D,_=layers(n,gg)
    return D,sum(1 for g in gg if g[0]=='cx')
if __name__=="__main__":
    DX=pickle.load(open(sys.argv[1],'rb')); DY=pickle.load(open(sys.argv[2],'rb'))
    seed=int(sys.argv[3]); iters=int(sys.argv[4]); out=sys.argv[5]
    tot,pen,kg,err=run_ksa(DX,DY,seed=seed,iters=iters)
    print([l for l in err.split("\n") if l.startswith('init')], err.strip().split("\n")[-1])
    if pen==0:
        print("assembled",assemble(DX,DY,kg,out))
        pickle.dump(kg,open(out.replace('.qasm','_kernel.pkl'),'wb'))
