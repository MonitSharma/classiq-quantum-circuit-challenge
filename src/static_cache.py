from xag_phase import *
from mcz import phase_cube
import xag_phase
xag_phase.phase_cube=phase_cube
from collections import Counter
import pickle

def apply_path(q,g,path,wire,free,live):
 for v in path:
  a,b=g.nodes[v];pre,p,r=linear(q,a,b,wire)
  if v in live:t=wire[v]
  else:t=free.pop(0);wire[v]=t
  q.compose(pre,inplace=True);q.rccx(p,r,t);q.compose(pre.inverse(),inplace=True)
  if v in live:live.remove(v);free.append(wire.pop(v));free.sort()
  else:live.add(v)

def solve(terms,cached,g=None,roots=None,fast=False):
 if g is None:g,roots=make_graph(terms)
 start=frozenset(cached)
 # Static cache consists of input-only AND nodes.
 wire={i:i for i in range(12)};free=list(range(12,18));live=set();pre=QuantumCircuit(18)
 apply_path(pre,g,list(cached),wire,free,live)
 out=pre.copy();records=[];total=0
 for k,root in enumerate(roots):
  best=None;bs=1e9;choice=None
  options=[]
  for fs in alternatives(g,root,maxf=5):
   try:path=plan(g,start,fs,max_states=20000)
   except ValueError:continue
   # cost proxy includes number of nonlinear compute/uncompute operations
   proxy=6*len(path)+max(0,len(fs)-2)*10
   options.append((proxy,fs,path))
  options.sort(key=lambda z:z[0])
  for _,fs,path in options[:(2 if fast else 10)]:
   q=QuantumCircuit(18);w=wire.copy();f=free.copy();l=live.copy()
   apply_path(q,g,path,w,f,l);undo=q.inverse();phase_many(q,fs,w,f);q.compose(undo,inplace=True)
   qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
   sc=qc.depth()
   if sc<bs:best=qc;bs=sc;choice=(fs,path)
  if best is None:raise ValueError('no path')
  total+=bs;out.compose(best,inplace=True);records.append(choice)
 out.compose(pre.inverse(),inplace=True)
 return out,records,total

if __name__=='__main__':
 ts=json.loads(Path('artifacts/pair_terms.json').read_text());g,roots=make_graph(ts)
 freq=Counter(v for r in roots for v in g.ancestors(r))
 leaf=[v for v,p in g.nodes.items() if not any(u>=12 for f in p for u in f)]
 leaf.sort(key=lambda v:freq[v],reverse=True)
 print('leaves',[(v,freq[v]) for v in leaf],flush=True)
 options=[()]+[(v,) for v in leaf[:14]]+list(itertools.combinations(leaf[:12],2))
 best=999999
 for i,cached in enumerate(options):
  try:q,ch,total=solve(ts,cached,g,roots,fast=True)
  except ValueError:continue
  qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
  if q.depth()<qc.depth():qc=q
  if qc.depth()<best:
   best=qc.depth();print(i,cached,'best',best,'cx',qc.count_ops().get('cx'),flush=True)
   Path('artifacts/static.qasm').write_text(qasm2.dumps(qc));Path('artifacts/static_config.pkl').write_bytes(pickle.dumps((ts,cached,ch)))
  if i%10==0:print('progress',i,flush=True)
