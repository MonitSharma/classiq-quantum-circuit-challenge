import pickle, sys, math, numpy as np
from build import loader_ops, inverse_ops, emit, u3m
from sim import symbolic_final
from qa import parse, layers
from kperm import kernel_action
def build2(xp, yp, kpath, out):
    X=pickle.load(open(xp,'rb')); Y=pickle.load(open(yp,'rb'))
    xg=X['gates']+[(('cx',),c,t) for c,t in X['fix']]; yg=Y['gates']+[(('cx',),c,t) for c,t in Y['fix']]
    rx=symbolic_final(xg); ry=symbolic_final(yg)
    xw=[0,1,2,3,4,5,15,16,17]; yw=[6,7,8,9,10,11,12,13,14]
    def place(rows,req,al,wl):
        o=[]; used=set()
        for v,A in zip(req,al):
            w=[w for w in sorted(A) if rows[w]==v and w not in used][0]; used.add(w); o.append(wl[w])
        return o
    px=place(rx,X['req'],X['al'],xw); py=place(ry,Y['req'],Y['al'],yw)
    kernel_wires=py+px
    res=kernel_action(kpath); perm={}
    for j in range(8):
        for i in range(8):
            if all(((res[b][0]>>j)&1)==((b>>i)&1) for b in range(256)): perm[j]=i
    for j,i in perm.items():
        if i!=j: assert kernel_wires[i]>=12 and kernel_wires[j]>=12, "permuted kernel wire must be an ancilla"
    remap={w:w for w in range(18)}
    for j,i in perm.items(): remap[kernel_wires[i]]=kernel_wires[j]
    Lops=loader_ops(xg,xw)+loader_ops(yg,yw)
    n,kg=parse(kpath); Kops=[]
    for g in kg:
        if g[0]=='cx': Kops.append(('cx',kernel_wires[g[1][0]],kernel_wires[g[1][1]]))
        else: Kops.append(('1q',kernel_wires[g[1][0]],u3m(*[float(eval(a.replace('pi','math.pi'))) for a in g[2].split(',')])))
    inv=[]
    for o in inverse_ops(Lops):
        inv.append(('cx',remap[o[1]],remap[o[2]]) if o[0]=='cx' else ('1q',remap[o[1]],o[2]))
    open(out,'w').write(emit(Lops+Kops+inv))
    n,gg=parse(out); D,_=layers(n,gg)
    return D, sum(1 for g in gg if g[0]=='cx'), kernel_wires
if __name__=="__main__":
    print(build2(*sys.argv[1:5]))
