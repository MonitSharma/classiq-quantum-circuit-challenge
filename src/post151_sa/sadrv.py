import subprocess, pickle, sys, os, random
from sim import check_loader2, symbolic_final
from depth import gate_depth
def run_sa(D, seed=1, iters=20000000, T0=2.0, T1=0.05, lam=3.0, mu=0.05, init=None, tag="sa", cut=0):
    targets=D['targets']
    plist=[(m,i,a) for i in range(3) for m,a in targets[i].items()]
    if init is None:
        init=[(g[1],g[2]) for g in D['gates'] if g[0][0]=='cx']+list(D.get('fix',[]))
    lines=[str(len(plist))]+[f"{m} {i}" for m,i,a in plist]
    lines.append(str(len(D['req'])))
    for v,A in zip(D['req'],D['al']): lines.append(f"{v} {sum(1<<w for w in A)}")
    lines.append(str(len(init)))+0 if False else None
    lines.append(str(len(init))); lines+= [f"{c} {t}" for c,t in init]
    out=f"/tmp/scratch/a/runs/{tag}_{seed}.txt"
    r=subprocess.run(["./c/sa",str(seed),str(iters),str(T0),str(T1),str(lam),str(mu),out,str(cut)],input="\n".join(lines)+"\n",capture_output=True,text=True)
    txt=open(out).read().split("\n")
    d,pen,L=map(int,txt[0].split())
    gates=[]
    for line in txt[1:]:
        if not line: continue
        t=line.split()
        if t[0]=='H': gates.append((('h',),int(t[1])))
        elif t[0]=='R': gates.append((('rz',plist[int(t[2])][2]),int(t[1])))
        else: gates.append((('cx',),int(t[1]),int(t[2])))
    return d,pen,gates,r.stderr
if __name__=="__main__":
    src=sys.argv[1]; seed=int(sys.argv[2]); iters=int(sys.argv[3]); tag=sys.argv[4]
    D=pickle.load(open(src,'rb'))
    d,pen,gates,err=run_sa(D,seed=seed,iters=iters,tag=tag)
    print(err.strip().split("\n")[-1])
    if pen==0:
        chk=check_loader2(gates,D['newcode'])
        rows=symbolic_final(gates)
        ok=all(any(rows[w]==v for w in A) for v,A in zip(D['req'],D['al']))
        print("SA depth",d,"gate_depth",gate_depth(gates),"dev %.1e"%chk['max_dev'],"placement ok",ok)
        D2=dict(D); D2['gates']=gates; D2['fix']=[]; D2['depth']=gate_depth(gates)
        pickle.dump(D2,open(f"runs/{tag}_{seed}.pkl","wb"))
