from xag import *
from factor import phase_cube

def linear_many(forms,wire):
 rows=[(set(wire[v] for v in f if v!=-1),int(-1 in f)) for f in forms]
 pivots=[];pre=QuantumCircuit(18)
 while rows:
  a,k=rows.pop(0)
  available=a-set(pivots)
  if not available:
   # previous mapped coordinates are constrained to one; evaluate dependent form.
   if (len(a)%2)^k !=1:return None,[]
   continue
  p=min(available)
  for c in sorted(a-{p}):
   pre.cx(c,p)
   rows=[((b^{c}) if p in b else b,z) for b,z in rows]
  if k:
   pre.x(p);rows=[(b,z^(p in b)) for b,z in rows]
  pivots.append(p)
 return pre,pivots

def phase_many(q,forms,wire,free):
 pre,vs=linear_many(forms,wire)
 if pre is None:return
 q.compose(pre,inplace=True);phase_cube(q,frozenset(v+1 for v in vs),[v+1 for v in free]);q.compose(pre.inverse(),inplace=True)

def alternatives(g,root,maxf=6):
 seen=set();stack=[tuple(root)]
 while stack:
  fs=stack.pop();key=tuple(sorted(fs,key=lambda f:tuple(sorted(f))))
  if key in seen:continue
  seen.add(key);yield fs
  if len(fs)>=maxf:continue
  for i,f in enumerate(fs):
   if len(f)==1 and next(iter(f))>=12:
    a,b=g.nodes[next(iter(f))];stack.append(fs[:i]+(a,b)+fs[i+1:])

def make_one(g,forms,path):
 q=QuantumCircuit(18);wire={v:v for v in range(12)};free=list(range(12,18));live=set()
 for v in path:
  a,b=g.nodes[v];pre,p,r=linear(q,a,b,wire)
  if v in live:t=wire[v]
  else:t=free.pop(0);wire[v]=t
  q.compose(pre,inplace=True);q.rccx(p,r,t);q.compose(pre.inverse(),inplace=True)
  if v in live:live.remove(v);free.append(wire.pop(v));free.sort()
  else:live.add(v)
 undo=q.inverse();phase_many(q,forms,wire,free);q.compose(undo,inplace=True)
 return q

def build_best(terms):
 g,roots=make_graph(terms);out=QuantumCircuit(18);chosen=[]
 for k,root in enumerate(roots):
  best=None;bs=1e9
  for fs in alternatives(g,root):
   try:path=plan(g,frozenset(),fs,max_states=30000)
   except ValueError:continue
   q=make_one(g,fs,path)
   qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
   s=qc.depth()
   if s<bs:bs=s;best=qc;choice=(fs,path)
  if best is None:raise ValueError('no path')
  print('term',k,'depth',bs,flush=True);out.compose(best,inplace=True);chosen.append(choice)
 return out,chosen
if __name__=='__main__':
 ts=json.loads(Path('artifacts/rank_terms.json').read_text())
 q,ch=build_best(ts);qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
 print('result',qc.depth(),qc.count_ops(),flush=True)
 Path('artifacts/xag_phase.qasm').write_text(qasm2.dumps(qc))
