from formula import *
import heapq
from collections import Counter
FULL=(1<<4096)-1
INPUT_TT=[sum(1<<i for i in range(4096) if i>>b&1) for b in range(12)]
class Graph:
 def __init__(self):
  self.nodes={};self.tt={i:t for i,t in enumerate(INPUT_TT)};self.basis={};self.next=12
  self.insert(FULL,frozenset([-1]))
  for i,t in self.tt.items():self.insert(t,frozenset([i]))
 def insert(self,t,form):
  while t:
   p=t.bit_length()-1
   if p in self.basis:
    bt,bf=self.basis[p];t^=bt;form^=bf
   else:self.basis[p]=(t,form);return
 def lookup(self,t):
  f=frozenset()
  while t:
   p=t.bit_length()-1
   if p not in self.basis:return None
   bt,bf=self.basis[p];t^=bt;f^=bf
  return f
 def value(self,f):
  t=0
  for v in f:t ^= FULL if v==-1 else self.tt[v]
  return t
 def expr(self,e):
  if isinstance(e,int):return frozenset([-1]) if e else frozenset()
  if e[0]=='v':return frozenset([e[1]])
  a=self.expr(e[1])
  if e[0]=='not':return a^{-1}
  b=self.expr(e[2])
  if e[0]=='xor':return a^b
  t=self.value(a)&self.value(b);f=self.lookup(t)
  if f is not None and len(f-{-1})<=1:return f
  n=self.next;self.next+=1;self.nodes[n]=(a,b);self.tt[n]=t;f=frozenset([n]);self.insert(t,f);return f
 def ancestors(self,forms):
  out=set(v for f in forms for v in f if v>=12);stack=list(out)
  while stack:
   v=stack.pop()
   for f in self.nodes[v]:
    for u in f:
     if u>=12 and u not in out:out.add(u);stack.append(u)
  return out

def linear(q,a,b,wire):
 # Map two independent linear forms to physical pivot wires using reversible CNOTs.
 forms=[set(wire[v] for v in f if v!=-1) for f in (a,b)]
 const=[-1 in a,-1 in b];pre=QuantumCircuit(18)
 # select pivot of first which leaves second nonempty after elimination
 if not forms[0] or not forms[1] or forms[0]==forms[1]:raise ValueError('dependent forms')
 p=min(forms[0]-forms[1]) if forms[0]-forms[1] else min(forms[0])
 for c in sorted(forms[0]-{p}):
  pre.cx(c,p)
  if p in forms[1]:
   if c in forms[1]:forms[1].remove(c)
   else:forms[1].add(c)
 forms[0]={p}
 candidates=forms[1]-{p}
 if not candidates:raise ValueError('dependent')
 r=min(candidates)
 for c in sorted(forms[1]-{r}):pre.cx(c,r)
 if const[0]:pre.x(p)
 if const[1]:pre.x(r)
 return pre,p,r

def phase_forms(q,a,b,wire):
 if not a or not b:return
 if a==b:single=a
 elif a==b^{-1}:return
 elif a==frozenset([-1]):single=b
 elif b==frozenset([-1]):single=a
 else:
  pre,p,r=linear(q,a,b,wire);q.compose(pre,inplace=True);q.cz(p,r);q.compose(pre.inverse(),inplace=True);return
 for v in single:
  if v==-1:q.global_phase+=np.pi
  else:q.z(wire[v])

def make_graph(terms):
 g=Graph();roots=[]
 for x,y in terms:
  roots.append((g.expr(remap(formula(x,6),range(6))),g.expr(remap(formula(y,6),range(6,12)))))
 return g,roots

def plan(g,live,targets,limit=6,max_states=300000):
 required=frozenset(v for f in targets for v in f if v>=12)
 scope=g.ancestors(targets)|g.ancestors([live])|set(live)
 ids=sorted(scope);pos={v:i for i,v in enumerate(ids)}
 deps={v:sum(1<<pos[u] for f in g.nodes[v] for u in set(f) if u>=12) for v in []}
 # OR dependencies, not sum (duplicates may occur in both linear forms)
 deps={v:sum(1<<pos[u] for u in set().union(*g.nodes[v]) if u>=12) for v in ids}
 goal=sum(1<<pos[v] for v in required);start=sum(1<<pos[v] for v in live)
 # relevant ancestor closure lower bound for missing computations
 anc=g.ancestors(targets);ancmask=sum(1<<pos[v] for v in anc)
 def h(s):return (ancmask&~s).bit_count() if goal else s.bit_count()
 dist={start:0};parent={};queue=[(h(start),0,start)]
 while queue:
  _,d,s=heapq.heappop(queue)
  if d!=dist.get(s):continue
  if ((s&goal)==goal) if goal else s==0:
   path=[]
   while s!=start:
    prev,v=parent[s];path.append(v);s=prev
   return path[::-1]
  if len(dist)>max_states:raise ValueError('search size')
  width=s.bit_count()
  for v in ids:
   bit=1<<pos[v]
   if s&deps[v]!=deps[v]:continue
   if not(s&bit) and width>=limit:continue
   z=s^bit;dd=d+1
   if dd<dist.get(z,1e9):
    dist[z]=dd;parent[z]=(s,v);heapq.heappush(queue,(dd+h(z),dd,z))
 raise ValueError('not pebbleable')

def build(terms,order=None,clear_each=False):
 g,roots=make_graph(terms);q=QuantumCircuit(18);wire={v:v for v in range(12)};live=set();free=list(range(12,18))
 def toggle(v):
  a,b=g.nodes[v];pre,p,r=linear(q,a,b,wire)
  if v in live:t=wire[v]
  else:t=free.pop(0);wire[v]=t
  q.compose(pre,inplace=True);q.rccx(p,r,t);q.compose(pre.inverse(),inplace=True)
  if v in live:live.remove(v);free.append(wire.pop(v));free.sort()
  else:live.add(v)
 history=[]
 for i in (range(len(roots)) if order is None else order):
  path=plan(g,frozenset(live),roots[i])
  for v in path:toggle(v)
  history+=path;phase_forms(q,*roots[i],wire)
  if clear_each:
   for v in reversed(history):toggle(v)
   history=[]
 # reversing whole history incurs duplicates, cancel adjacent identical toggles algebraically.
 for v in plan(g,frozenset(live),[]):toggle(v)
 assert not live
 return q,g,roots

if __name__=='__main__':
 for name,ts in [('nested',nested_terms()),('rank',json.loads(Path('artifacts/rank_terms.json').read_text()))]:
  g,r=make_graph(ts);print(name,'AND nodes',len(g.nodes),'root sizes',[len(g.ancestors(p)) for p in r],flush=True)
  for separate in [True,False]:
   try:q,g,r=build(ts,clear_each=separate)
   except ValueError as e:print('skip',e,flush=True);continue
   out=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
   print(name,separate,out.depth(),out.count_ops(),flush=True)
   Path(f'artifacts/xag_{name}_{separate}.qasm').write_text(qasm2.dumps(out))
