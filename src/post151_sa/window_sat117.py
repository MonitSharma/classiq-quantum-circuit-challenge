"""Exact SAT replacement of central synchronous layer windows.

The local parity network has fixed input/output linear maps and fixed phase
polynomial. Each successful replacement is replayed and independently verified.
"""
import argparse,sys,json,time,math,itertools,multiprocessing as mp
from pathlib import Path
from collections import defaultdict
import numpy as np
from postopt import parse_ops,fuse,write,depth
from canc import simplify
from ksat import Enc

def encode(n,goal,terms,T):
 E=Enc();one=E.var();E.add(one);R={(w,0):[one if j==w else -one for j in range(n)] for w in range(n)};X={};F={}
 for t in range(1,T+1):
  for a,b in itertools.permutations(range(n),2):X[a,b,t]=E.var()
  for w in range(n):
   inv=[X[a,b,t] for a,b in itertools.permutations(range(n),2) if w in (a,b)]
   for u,v in itertools.combinations(inv,2):E.add(-u,-v)
  for w in range(n):
   rr=[]
   for k in range(n):
    ys=[]
    for a in range(n):
     if a==w:continue
     x=X[a,w,t];v=R[a,t-1][k]
     if v==-one:continue
     if v==one:ys.append(x);continue
     y=E.var();E.add(-y,x);E.add(-y,v);E.add(y,-x,-v);ys.append(y)
    if not ys:rr.append(R[w,t-1][k]);continue
    v=ys[0] if len(ys)==1 else E.var()
    if len(ys)>1:
     E.add(-v,*ys)
     for y in ys:E.add(v,-y)
    old=R[w,t-1][k];nw=E.var()
    E.add(-nw,old,v);E.add(-nw,-old,-v);E.add(nw,-old,v);E.add(nw,old,-v);rr.append(nw)
   R[w,t]=rr
 for w in range(n):
  for k,v in enumerate(R[w,T]):E.add(v if goal[w]>>k&1 else -v)
 for m in terms:
  opts=[]
  for t in range(1,T+1):
   for w in range(n):
    r=R[w,t-1]
    if any(abs(v)==one and (v==one)!=bool(m>>k&1) for k,v in enumerate(r)):continue
    f=E.var();F[m,w,t]=f;opts.append(f)
    for k,v in enumerate(r):E.add(-f,v if m>>k&1 else -v)
    for a in range(n):
     if a!=w:E.add(-f,-X[a,w,t]);E.add(-f,-X[w,a,t])
  E.add(*opts)
 return E,X,F

def solve_worker(conn,n,goal,angles,T,hints):
 from pysat.solvers import Solver
 start=time.monotonic();E,X,F=encode(n,goal,angles,T)
 with Solver(name='cadical195',bootstrap_with=E.cl) as s:
  if hints:s.set_phases([v if key in hints else -v for key,v in X.items()])
  sat=s.solve();model=set(s.get_model() or [])
  if sat:
   cx=[key for key,v in X.items() if v in model];seen=set();rot=[]
   for (m,w,t),v in F.items():
    if v in model and m not in seen:seen.add(m);rot.append((m,w,t))
   assert seen==set(angles)
   conn.send(dict(status='SAT',cx=cx,rot=rot,seconds=time.monotonic()-start,vars=E.n,clauses=len(E.cl)))
  else:conn.send(dict(status='UNSAT',seconds=time.monotonic()-start,vars=E.n,clauses=len(E.cl)))
 conn.close()

def bounded(n,goal,angles,T,hints,seconds):
 ctx=mp.get_context('fork');parent,child=ctx.Pipe();p=ctx.Process(target=solve_worker,args=(child,n,goal,angles,T,hints));p.start();child.close()
 if parent.poll(seconds):r=parent.recv();p.join(2)
 else:r=dict(status='TIMEOUT');p.terminate();p.join()
 parent.close();return r

def layerize(ops):
 times=[0]*18;layers=defaultdict(list)
 for o in ops:
  t=max(times[w] for w in o[1])+1
  for w in o[1]:times[w]=t
  layers[t].append(o)
 return layers

def window(layers,a,b):
 old=[g for t in range(a,b+1) for g in layers[t]];wires=sorted({w for g in old for w in g[1]});ids={w:i for i,w in enumerate(wires)};n=len(wires);rows=[1<<w for w in range(n)];angles={};hints=set()
 for t in range(a,b+1):
  for g in layers[t]:
   if g[0]=='cx':
    c,u=map(ids.get,g[1]);rows[u]^=rows[c];hints.add((c,u,t-a+1))
   else:
    if abs(g[2][0,1])+abs(g[2][1,0])>1e-10:return None
    m=rows[ids[g[1][0]]];angles[m]=angles.get(m,0)+np.angle(g[2][1,1]/g[2][0,0])
 angles={m:(v+math.pi)%(2*math.pi)-math.pi for m,v in angles.items()};angles={m:v for m,v in angles.items() if abs(v)>1e-10}
 return wires,rows,angles,hints

def decode(r,wires,goal,angles,T):
 rows=[1<<w for w in range(len(wires))];out=[];seen=set()
 for t in range(1,T+1):
  used=set()
  for m,w,t0 in r['rot']:
   if t0!=t:continue
   assert rows[w]==m and w not in used;used.add(w);seen.add(m);out.append(('u3',(wires[w],),np.diag([1,np.exp(1j*angles[m])])) )
  for c,u,t0 in r['cx']:
   if t0!=t:continue
   assert c not in used and u not in used;used.update([c,u]);rows[u]^=rows[c];out.append(('cx',(wires[c],wires[u]),None))
 assert rows==goal and seen==set(angles)
 return out

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',default='artifacts/rewrite117_20260922/windows');p.add_argument('--reverse',action='store_true');p.add_argument('--seconds',type=float,default=3);p.add_argument('--start',type=int,default=47);p.add_argument('--end',type=int,default=70);p.add_argument('--lengths',default='3,4,5,6,7,8');a=p.parse_args()
 out=Path(a.outdir);out.mkdir(exist_ok=True);base=fuse(parse_ops('artifacts/117/conditional_loader_117_cx577.qasm'));layers=layerize(base);records=[]
 # Positive control: known 5-layer circuit solved at its actual length.
 w,goal,angles,hints=window(layers,48,52);r=bounded(len(w),goal,angles,5,hints,15);assert r['status']=='SAT',r;decode(r,w,goal,angles,5);print('CONTROL',r['status'],r['seconds'],flush=True)
 for length in map(int,a.lengths.split(',')):
  for lo in (reversed(range(a.start,a.end-length+2)) if a.reverse else range(a.start,a.end-length+2)):
   hi=lo+length-1;spec=window(layers,lo,hi)
   if spec is None:continue
   w,goal,angles,hints=spec;r=bounded(len(w),goal,angles,length-1,hints,a.seconds);r.update(lo=lo,hi=hi,length=length,n=len(w),terms=len(angles));records.append(r)
   print({k:v for k,v in r.items() if k not in ('cx','rot')},flush=True)
   if r['status']=='SAT':
    repl=decode(r,w,goal,angles,length-1);ops=[g for t in sorted(layers) if t<lo for g in layers[t]]+repl+[g for t in sorted(layers) if t>hi for g in layers[t]];ops=fuse(simplify(fuse(ops),False));path=out/f'window_{lo}_{hi}_d{depth(ops)}.qasm';write(ops,path);r['path']=str(path);r['depth']=depth(ops)
    sys.path.insert(0,'src');from classiq_synth.core.verify import exhaustive_verify
    r['verification']=exhaustive_verify(path);print('VERIFIED',r['depth'],path,flush=True)
    if r['depth']<117:
     (out/'report.json').write_text(json.dumps(records,indent=2));sys.exit(0)
   (out/'report.json').write_text(json.dumps(records,indent=2))
 print('DONE',len(records),flush=True)
