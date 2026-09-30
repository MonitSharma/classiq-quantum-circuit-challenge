import pickle, subprocess, sys
from sim import check_loader2
from depth import gate_depth
def load_beam(path):
    lines=open(path).read().split('\n'); d=int(lines[0].split()[0]); seq=[]
    for l in lines[1:d+1]:
        t=list(map(int,l.split()))
        for q in range(t[0]): seq.append((t[1+2*q],t[2+2*q]))
    return d,seq
def sa4(D,init,seed=1,iters=0,T0=0.5,T1=0.02,lam=4,mu=0.03,binary='./c/sa4',tag='lb'):
    targets=D['targets']; plist=[(m,i,a) for i in range(3) for m,a in targets[i].items()]
    inp=[str(len(plist))]+[f"{m} {i}" for m,i,a in plist]+["0","0",str(len(init))]+[f"{c} {t}" for c,t in init]
    out=f"runs/{tag}_{seed}.txt"
    r=subprocess.run([binary,str(seed),str(iters),str(T0),str(T1),str(lam),str(mu),out],input="\n".join(inp)+"\n",capture_output=True,text=True)
    txt=open(out).read().split("\n"); d,pen,L=map(int,txt[0].split()); gates=[]
    for line in txt[1:]:
        if not line: continue
        t=line.split()
        if t[0]=='H': gates.append((('h',),int(t[1])))
        elif t[0]=='R': gates.append((('rz',plist[int(t[2])][2]),int(t[1])))
        else: gates.append((('cx',),int(t[1]),int(t[2])))
    return d,pen,gates
if __name__=="__main__":
    D=pickle.load(open(sys.argv[1],'rb')); bd,seq=load_beam(sys.argv[2])
    d,pen,g=sa4(D,seq)
    chk=check_loader2(g,D['newcode'])
    print('beam layers',bd,'sa4 depth',d,'pen',pen,'gate_depth',gate_depth(g),'dev %.1e'%chk['max_dev'])
