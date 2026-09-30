import pickle, sys, time
from satwin import *
from sim import check_loader2, symbolic_final
from depth import gate_depth
src=sys.argv[1]; out=sys.argv[2]; a=int(sys.argv[3]); dec=int(sys.argv[4]); tmo=int(sys.argv[5])
D=pickle.load(open(src,'rb')); pl,pidx=plist_of(D)
gates=D['gates']+[(('cx',),c,t) for c,t in D.get('fix',[])]
layers=layerize(gates); states,recs=replay(layers,len(layers),pidx,pl)
n=len(recs); print("layers",n,"tail from",a,"len",n-a, "closed at a",states[a][1], flush=True)
b=n
for Wn in range(n-a-1, n-a-1-dec, -1):
    t0=time.time()
    res=solve_window(pl,states[a],states[b],recs[a:b],Wn,final=True,req=D['req'],al=D['al'],timeout=tmo)
    print("Wn",Wn,"->", "SAT" if res else ("UNSAT" if res is False else "TIMEOUT"), "t %.0f"%(time.time()-t0), flush=True)
    if not res: break
    newrecs=recs[:a]+res
    g=recs_to_gates(newrecs,pl); chk=check_loader2(g,D['newcode']); rows=symbolic_final(g)
    ok=all(any(rows[w]==v for w in A) for v,A in zip(D['req'],D['al']))
    print("  gate_depth",gate_depth(g),"dev %.1e"%chk['max_dev'],"placement",ok,flush=True)
    if chk['max_dev']<1e-9 and ok:
        D2=dict(D); D2['gates']=g; D2['fix']=[]; D2['depth']=gate_depth(g); pickle.dump(D2,open(out,'wb'))
