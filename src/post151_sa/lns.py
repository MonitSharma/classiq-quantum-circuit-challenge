import pickle, sys, time, random
from satwin import *
from sim import check_loader2, symbolic_final
from depth import gate_depth
src=sys.argv[1]; out=sys.argv[2]; W=int(sys.argv[3]); budget=float(sys.argv[4]); tmo=int(sys.argv[5]) if len(sys.argv)>5 else 30
D=pickle.load(open(src,'rb')); pl,pidx=plist_of(D)
gates=D['gates']+[(('cx',),c,t) for c,t in D.get('fix',[])]
layers=layerize(gates); states,recs=replay(layers,len(layers),pidx,pl)
print("start layers",len(recs),"gate_depth",gate_depth(gates),flush=True)
t0=time.time(); rng=random.Random(1); improved=True; stats=[]
while time.time()-t0<budget and improved:
    improved=False
    starts=list(range(1,len(recs)-1)); rng.shuffle(starts)
    for a in starts:
        if time.time()-t0>budget: break
        b=min(len(recs),a+W); Wn=(b-a)-1
        if Wn<1: continue
        final=(b==len(recs))
        res=solve_window(pl,states[a],states[b],recs[a:b],Wn,final=final,req=D['req'],al=D['al'],timeout=tmo)
        stats.append((a,b,'SAT' if res else ('UNSAT' if res is False else 'TO')))
        if res:
            newrecs=recs[:a]+res+recs[b:]
            g=recs_to_gates(newrecs,pl)
            chk=check_loader2(g,D['newcode']); rows=symbolic_final(g)
            ok=all(any(rows[w]==v for w in A) for v,A in zip(D['req'],D['al']))
            if chk['max_dev']<1e-9 and ok:
                layers=layerize(g); states,recs=replay(layers,len(layers),pidx,pl)
                print("window",a,b,"-> layers",len(recs),"gate_depth",gate_depth(g),"t %.0f"%(time.time()-t0),flush=True)
                D2=dict(D); D2['gates']=g; D2['fix']=[]; D2['depth']=gate_depth(g); pickle.dump(D2,open(out,'wb'))
                improved=True; break
            else:
                print("window",a,b,"SAT but invalid", chk['max_dev'], ok, flush=True)
print("done", len(recs), "stats", {s:sum(1 for x in stats if x[2]==s) for s in ('SAT','UNSAT','TO')})
