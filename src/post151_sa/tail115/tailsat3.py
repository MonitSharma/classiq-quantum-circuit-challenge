"""Tail SAT re-synthesis with per-code-row constraints.
usage: tailsat3.py src.pkl out.pkl a Wn tmo 'json-spec'
spec keys: idle {req_idx:k}, notarget {req_idx:k}, fixwire 0/1 (keep champion wire per req), close_by {label:layer_abs}
"""
import pickle, sys, time, json
from satwin3 import *
from sim import check_loader2, symbolic_final
from depth import gate_depth
src,out=sys.argv[1],sys.argv[2]; a=int(sys.argv[3]); Wn=int(sys.argv[4]); tmo=int(sys.argv[5]); spec=json.loads(sys.argv[6]) if len(sys.argv)>6 else {}
D=pickle.load(open(src,'rb')); pl,pidx=plist_of(D)
gates=D['gates']+[(('cx',),c,t) for c,t in D.get('fix',[])]
layers=layerize(gates); states,recs=replay(layers,len(layers),pidx,pl)
n=len(recs); print("layers",n,"window",a,"->",a+Wn,"(orig",n-a,") closed at a",states[a][1],"spec",spec, flush=True)
al=D['al']
if spec.get('fixwire'):
    fin=states[-1][0]; al=[{w for w in range(NV) if fin[w]==v} for v in D['req']]
    print("fixed wires",al)
idle={int(k):v for k,v in spec.get('idle',{}).items()}
nt={int(k):v for k,v in spec.get('notarget',{}).items()}
cb={int(k):v-a for k,v in spec.get('close_by',{}).items()}
t0=time.time()
res=solve_window(pl,states[a],states[n],recs[a:n],Wn,final=True,req=D['req'],al=al,timeout=tmo,idle_last=idle,notarget_last=nt,close_by=cb)
print("Wn",Wn,"->", "SAT" if res else ("UNSAT" if res is False else "TIMEOUT"), "t %.0f"%(time.time()-t0), flush=True)
if res:
    newrecs=recs[:a]+res
    g=recs_to_gates(newrecs,pl); chk=check_loader2(g,D['newcode']); rows=symbolic_final(g)
    ok=all(any(rows[w]==v for w in A) for v,A in zip(D['req'],D['al']))
    print("  gate_depth",gate_depth(g),"dev %.1e"%chk['max_dev'],"placement",ok,flush=True)
    for k in range(max(0,len(newrecs)-14),len(newrecs)): print(k+1,newrecs[k])
    if chk['max_dev']<1e-9 and ok:
        D2=dict(D); D2['gates']=g; D2['fix']=[]; D2['depth']=gate_depth(g); pickle.dump(D2,open(out,'wb')); print("saved",out)
