from radius_circuit import *
from functools import lru_cache

def shrink(table,n,b,val):
 return tuple(table[(i&((1<<b)-1))|((i>>b)<<(b+1))|(val<<b)] for i in range(1<<(n-1)))

def primitive(table,n):
 cubes={}
 for bit in range(3):
  t=sum(((v>>bit)&1)<<i for i,v in enumerate(table))
  for m,v in esop(t,n):cubes[m,v]=cubes.get((m,v),0)^(1<<bit)
 return [(m,v,o) for (m,v),o in cubes.items() if o]

def gatecost(n,free):
 if n<=1:return 1
 if n==2:return 3
 if n==3:return 6
 if free: return 12+gatecost(n-2,free-1)
 return 2**n # fallback multiplexer-style relative rotation

@lru_cache(None)
def solve(table,n,parent,free):
 cubes=primitive(table,n)
 score=sum(gatecost(m.bit_count()+parent,free)+2*(o.bit_count()-1) for m,v,o in cubes)
 best=('leaf',cubes)
 if n==0:return score,best
 for b in range(n):
  lo=shrink(table,n,b,0);hi=shrink(table,n,b,1)
  if lo==hi:
   c,p=solve(lo,n-1,parent,free)
   if c<score:score=c;best=('skip',b,p)
   continue
  if parent and not free:continue
  extra=0 if not parent else (7 if any(lo) and any(hi) else 6)
  l,lp=solve(lo,n-1,True,free-parent);h,hp=solve(hi,n-1,True,free-parent)
  if l+h+extra<score:score=l+h+extra;best=('shannon',b,lp,hp,any(lo),any(hi))
  delta=tuple(a^b for a,b in zip(lo,hi))
  for base,pol in [(lo,1),(hi,0)]:
   l,lp=solve(base,n-1,parent,free);d,dp=solve(delta,n-1,True,free-parent)
   c=l+d+(6 if parent else 0)
   if c<score:score=c;best=('davio',b,lp,dp,pol)
 return score,best

def emit(q,p,variables,ctrl,free,outs):
 kind=p[0]
 if kind=='leaf':
  for m,v,o in p[1]:
   cs=[(variables[i]+1)*(1 if v>>i&1 else -1) for i in range(len(variables)) if m>>i&1]
   if ctrl is not None:cs.append(ctrl+1)
   if len(cs)>3 and not free:
    # Exact MCX fallback, safe on arbitrary dirty inputs.
    targets=[outs[i] for i in range(3) if o>>i&1];t=targets[0];neg=[-c-1 for c in cs if c<0]
    for a in targets[1:]:q.cx(t,a)
    if neg:q.x(neg)
    q.mcx([abs(c)-1 for c in cs],t)
    if neg:q.x(neg)
    for a in targets[1:]:q.cx(t,a)
   else:toggle_outputs(q,frozenset(cs),o,outs,free)
  return
 b=p[1];var=variables[b];remaining=variables[:b]+variables[b+1:]
 if kind=='skip':emit(q,p[2],remaining,ctrl,free,outs);return
 if kind=='davio':
  emit(q,p[2],remaining,ctrl,free,outs)
  pol=p[4]
  if pol==0:q.x(var)
  if ctrl is None:emit(q,p[3],remaining,var,free,outs)
  else:
   t=free[0];q.rccx(ctrl,var,t);emit(q,p[3],remaining,t,free[1:],outs);q.rccx(ctrl,var,t)
  if pol==0:q.x(var)
  return
 lp,hp,haslo,hashi=p[2:]
 if ctrl is None:
  if haslo:q.x(var);emit(q,lp,remaining,var,free,outs);q.x(var)
  if hashi:emit(q,hp,remaining,var,free,outs)
 else:
  t=free[0]
  if haslo:
   q.x(var);q.rccx(ctrl,var,t);q.x(var);emit(q,lp,remaining,t,free[1:],outs)
  if haslo and hashi:q.cx(ctrl,t)
  elif hashi:q.rccx(ctrl,var,t)
  if hashi:emit(q,hp,remaining,t,free[1:],outs);q.rccx(ctrl,var,t)
  elif haslo:q.x(var);q.rccx(ctrl,var,t);q.x(var)

def tree_qrom(seed=0):
 cubes=read_esop('experiments/radius.esop');cols,inv=out_basis(cubes)
 table=tuple(inv[radius(y)] for y in range(64));cost,p=solve(table,6,False,3)
 q=QuantumCircuit(18);emit(q,p,list(range(6,12)),None,[12,16,17],[13,14,15]);linear_output(q,cols,[13,14,15]);return q

if __name__=='__main__':
 import radius_circuit as rc
 q=tree_qrom();out=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
 print('lookup',out.depth(),out.count_ops(),flush=True)
 rc.qrom=tree_qrom;q=rc.build();print('full',q.depth(),q.count_ops(),flush=True);Path('artifacts/radius_tree.qasm').write_text(qasm2.dumps(q))
