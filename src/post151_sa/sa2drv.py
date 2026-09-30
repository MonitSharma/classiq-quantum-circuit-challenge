import subprocess, pickle, sys, random, time
from sim import check_loader2, symbolic_final
from depth import gate_depth
SC="/tmp/scratch/a"
def run_sa2(D, seed=1, iters=6000000, T0=0.8, T1=0.02, lam=4.0, mu=0.05, init=None, tag="sa2"):
    plist=[(m,i,a) for i in range(3) for m,a in D['targets'][i].items()]
    if init is None:
        init=[(100,6),(101,7),(102,8)]+[(g[1],g[2]) for g in D['gates'] if g[0][0]=='cx']+list(D.get('fix',[]))
    lines=[str(len(plist))]+[f"{m} {i}" for m,i,a in plist]+[str(len(D['req']))]+[f"{v} {sum(1<<w for w in A)}" for v,A in zip(D['req'],D['al'])]
    lines+=[str(len(init))]+[f"{c} {t}" for c,t in init]
    out=f"{SC}/runs/{tag}_{seed}.txt"
    r=subprocess.run([f"{SC}/c/sa2",str(seed),str(iters),str(T0),str(T1),str(lam),str(mu),out],input="\n".join(lines)+"\n",capture_output=True,text=True)
    txt=open(out).read().split("\n"); d,pen,L=map(int,txt[0].split())
    gates=[]; seq=[]
    for line in txt[1:]:
        if not line: continue
        t=line.split()
        if t[0]=='O': gates.append((('h','open',int(t[2])),int(t[1]))); seq.append((100+int(t[2]),int(t[1])))
        elif t[0]=='H': gates.append((('h',),int(t[1])))
        elif t[0]=='R': gates.append((('rz',plist[int(t[2])][2]),int(t[1])))
        else: gates.append((('cx',),int(t[1]),int(t[2]))); seq.append((int(t[1]),int(t[2])))
    return d,pen,gates,seq,r.stderr
if __name__=="__main__":
    src=sys.argv[1]; tag=sys.argv[2]; n=int(sys.argv[3]); iters=int(sys.argv[4]); base=int(sys.argv[5])
    D=pickle.load(open(src,'rb')); rng=random.Random(base); best=None; init=None
    for k in range(n):
        s=base+k; T0=rng.choice([0.5,0.8,1.2]); lam=rng.choice([3,4,6]); mu=rng.choice([0.0,0.05])
        d,pen,g,seq,err=run_sa2(D,seed=s,iters=iters,T0=T0,lam=lam,mu=mu,init=init,tag=tag)
        if pen: print("seed",s,"pen",pen,flush=True); continue
        rows=symbolic_final(g); ok=all(any(rows[w]==v for w in A) for v,A in zip(D['req'],D['al']))
        chk=check_loader2(g,D['newcode'])
        print("seed",s,"depth",d,gate_depth(g),"dev %.1e"%chk['max_dev'],"ok",ok,flush=True)
        if ok and chk['max_dev']<1e-9 and (best is None or d<best[0]):
            best=(d,g); D2=dict(D); D2['gates']=g; D2['fix']=[]; D2['depth']=d
            pickle.dump(D2,open(f"runs/{tag}_best.pkl","wb"))
            if rng.random()<0.5: init=seq   # sometimes chain from best
