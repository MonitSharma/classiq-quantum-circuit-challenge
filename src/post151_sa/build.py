import numpy as np, pickle, sys, re, math, json
from fixup import fixup
from sim import symbolic_final
from qa import parse
# ---------- single-qubit matrices & fusion ----------
def u3m(t,p,l):
    return np.array([[math.cos(t/2), -np.exp(1j*l)*math.sin(t/2)],
                     [np.exp(1j*p)*math.sin(t/2), np.exp(1j*(p+l))*math.cos(t/2)]])
def to_u3(U):
    a=abs(U[0,0]); b=abs(U[1,0])
    t=2*math.atan2(b,a)
    if b<1e-10:
        return (0.0,0.0,float(np.angle(U[1,1])-np.angle(U[0,0])))
    if a<1e-10:
        return (float(t),float(np.angle(U[1,0])),float(np.angle(-U[0,1])))
    ph=np.angle(U[0,0])
    return (float(t),float(np.angle(U[1,0])-ph),float(np.angle(-U[0,1])-ph))
def check_u3(U,par):
    V=u3m(*par); k=np.vdot(V.flatten(),U.flatten()); return np.max(np.abs(U - (k/abs(k))*V))
H=np.array([[1,1],[1,-1]])/np.sqrt(2)
def gate_matrix(g):
    if g[0]=='h': return H
    if g[0]=='rz': return np.diag([1,np.exp(1j*g[1])])
    if g[0]=='u3': return u3m(*g[1])
def emit(gatelist, n=18):
    """gatelist: ('cx',c,t) | ('1q',w,matrix). Fuse consecutive 1q per wire. returns qasm text"""
    if __import__('os').environ.get('PULL_CONTROL_RZ'):
        # Z-diagonal phases commute through a CX when they act on its control.
        # Pulling them left exposes the same value-fixed/control-side
        # overlap used by the endpoint-aware kernel model.  Do not cross a
        # CX where the phase wire is the target.
        gs=list(gatelist)
        for i in range(1,len(gs)):
            g=gs[i]
            if g[0] != '1q': continue
            U=g[2]
            if abs(U[0,1])>1e-10 or abs(U[1,0])>1e-10: continue
            j=i
            while j>0 and gs[j-1][0]=='cx' and gs[j-1][1]==g[1]:
                gs[j-1],gs[j]=gs[j],gs[j-1]; j-=1
        gatelist=gs
    pend=[None]*n; out=[]
    def flush(w):
        if pend[w] is not None:
            U=pend[w]
            if np.max(np.abs(U/ (U[0,0]/abs(U[0,0]) if abs(U[0,0])>1e-9 else 1) - np.eye(2)))>1e-12 or abs(abs(U[0,0])-1)>1e-12:
                par=to_u3(U); err=check_u3(U,par)
                if err>1e-9:
                    # fallback: numeric search on branch of cos
                    t,p,l=par
                    for alt in [(t,p,l),(t,p+math.pi,l+math.pi),(-t,p,l)]:
                        if check_u3(U,alt)<1e-9: par=alt; break
                    assert check_u3(U,par)<1e-9, (U,par)
                out.append(f"u3({par[0]!r},{par[1]!r},{par[2]!r}) q[{w}];")
            pend[w]=None
    for g in gatelist:
        if g[0]=='cx':
            flush(g[1]); flush(g[2]); out.append(f"cx q[{g[1]}],q[{g[2]}];")
        else:
            w=g[1]; pend[w]= g[2] if pend[w] is None else g[2]@pend[w]
    for w in range(n): flush(w)
    return 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[18];\n'+"\n".join(out)+"\n"
def loader_ops(gates, wiremap):
    ops=[]
    for g in gates:
        if g[0][0]=='cx': ops.append(('cx',wiremap[g[1]],wiremap[g[2]]))
        else: ops.append(('1q',wiremap[g[1]],gate_matrix(g[0])))
    return ops
def inverse_ops(ops):
    inv=[]
    for o in reversed(ops):
        if o[0]=='cx': inv.append(o)
        else: inv.append(('1q',o[1],o[2].conj().T))
    return inv
def load_pickle(path):
    D=pickle.load(open(path,'rb'))
    if isinstance(D,dict): return D['gates']
    return D[3] if len(D)==4 else D[2]
if __name__=="__main__":
    xg=load_pickle(sys.argv[1]); yg=load_pickle(sys.argv[2]); kpath=sys.argv[3]; out=sys.argv[4]
    xreq=[0x30,0x40,0x80,0x140]   # frame (1,2,5): L2 = L'0 ^ L'2
    if len(sys.argv)>5: xreq=[int(v,0) for v in sys.argv[5].split(',')]
    yreq=[0x20,0x40,0x80,0x100]
    from kperm import kernel_action
    from fixup2 import fixup2
    res0=kernel_action(kpath); moved=set()
    for j in range(8):
        for i in range(8):
            if all(((res0[b][0]>>j)&1)==((b>>i)&1) for b in range(256)) and i!=j: moved.add(i)
    anc={6,7,8}; allw=set(range(9))
    # kernel positions: 0 py,1-3 Ly, 4 px, 5-7 Lx
    yal=[anc if k in moved else allw for k in (0,1,2,3)]; xal=[anc if k in moved else allw for k in (4,5,6,7)]
    print("moved kernel positions",sorted(moved))
    RS=int(__import__('os').environ.get('FIXRS','1500'))
    bx=fixup2(xg,xreq,xal,restarts=RS,seed=1); by=fixup2(yg,yreq,yal,restarts=RS,seed=2)
    xg2=xg+[(('cx',),c,t) for c,t in bx[2]]; yg2=yg+[(('cx',),c,t) for c,t in by[2]]
    print("loader depths with fixup: x",bx[0],"y",by[0])
    rx=symbolic_final(xg2); ry=symbolic_final(yg2)
    xw=[0,1,2,3,4,5,15,16,17]; yw=[6,7,8,9,10,11,12,13,14]
    def place(rows,req,al,wl):
        out={}; used=set()
        for v,A in zip(req,al):
            w=[w for w in A if rows[w]==v and w not in used][0]; used.add(w); out[v]=wl[w]
        return out
    wx=place(rx,xreq,xal,xw); wy=place(ry,yreq,yal,yw)
    kernel_wires=[wy[yreq[0]],wy[yreq[1]],wy[yreq[2]],wy[yreq[3]],wx[xreq[0]],wx[xreq[1]],wx[xreq[2]],wx[xreq[3]]]
    print("kernel wires",kernel_wires)
    Lops=loader_ops(xg2,xw)+loader_ops(yg2,yw)
    n,kg=parse(kpath)
    Kops=[]
    for g in kg:
        if g[0]=='cx': Kops.append(('cx',kernel_wires[g[1][0]],kernel_wires[g[1][1]]))
        else:
            par=[float(eval(a.replace('pi','math.pi'))) for a in g[2].split(',')]
            Kops.append(('1q',kernel_wires[g[1][0]],u3m(*par)))
    from kperm import kernel_action
    res=kernel_action(kpath); perm={}
    for j in range(8):
        for i in range(8):
            if all(((res[b][0]>>j)&1)==((b>>i)&1) for b in range(256)): perm[j]=i
    remap={w:w for w in range(18)}
    for j,i in perm.items(): remap[kernel_wires[i]]=kernel_wires[j]
    inv=[]
    for o in inverse_ops(Lops):
        if o[0]=='cx': inv.append(('cx',remap[o[1]],remap[o[2]]))
        else: inv.append(('1q',remap[o[1]],o[2]))
    ops=Lops+Kops+inv
    text=emit(ops)
    open(out,'w').write(text)
    from qa import layers
    n,gg=parse(out); D,_=layers(n,gg)
    print("depth",D,"cx",sum(1 for g in gg if g[0]=='cx'),"u3",sum(1 for g in gg if g[0]=='u'))
