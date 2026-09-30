from formula import *
from factor import phase_cube

def factors(e):
 if not isinstance(e,int) and e[0]=='and':return factors(e[1])+factors(e[2])
 return [e]

def phase_product(q,exprs,free):
 exprs=[e for e in exprs if e!=1]
 if 0 in exprs:return
 # expand outer XOR, so large mixed functions can be phased directly
 for i,e in enumerate(exprs):
  if not isinstance(e,int) and e[0]=='xor':
   phase_product(q,exprs[:i]+factors(e[1])+exprs[i+1:],free)
   phase_product(q,exprs[:i]+factors(e[2])+exprs[i+1:],free)
   return
 cs=[];pres=[];free=list(free)
 for e in sorted(exprs,key=cost,reverse=True):
  if literal(e):cs.append((-1 if neg(e) else 1)*(var(e)+1))
  else:
   target=free.pop(0);pre=QuantumCircuit(18)
   compute(pre,e,target,free)
   q.compose(pre,inplace=True);pres.append(pre);cs.append(target+1)
 phase_cube(q,frozenset(cs),[i+1 for i in free])
 for pre in reversed(pres):q.compose(pre.inverse(),inplace=True)

def build(seed=0):
 terms=nested_terms();q=QuantumCircuit(18)
 rng=random.Random(seed)
 # factor common root AND components across phase products.
 products=[factors(remap(formula(x,6),range(6)))+factors(remap(formula(y,6),range(6,12))) for x,y in terms]
 def rec(products,free):
  if not products:return
  counts=Counter(e for p in products for e in p)
  pairs=Counter(tuple(sorted((a,b),key=str)) for p in products for a,b in itertools.combinations(p,2) if a!=b)
  opts=[]
  for pair,k in pairs.items():
   if k>1:opts.append(((k-1)*(cost(pair[0])+cost(pair[1])+1)*rng.uniform(.8,1.2),pair))
  if not opts or len(free)<3:
   for p in products:
    # compute each factor without expanding, permit clean auxiliaries
    cs=[];pres=[];avail=list(free)
    for e in sorted(p,key=cost,reverse=True):
     if literal(e):cs.append((-1 if neg(e) else 1)*(var(e)+1))
     else:
      target=avail.pop(0);pre=QuantumCircuit(18);compute(pre,e,target,avail)
      q.compose(pre,inplace=True);pres.append(pre);cs.append(target+1)
    phase_cube(q,frozenset(cs),[i+1 for i in avail])
    for pre in reversed(pres):q.compose(pre.inverse(),inplace=True)
   return
  _,pair=max(opts,key=lambda x:x[0]);a,b=pair;selected=[p for p in products if a in p and b in p];rest=[p for p in products if not (a in p and b in p)]
  pre=QuantumCircuit(18);compute(pre,And(a,b),free[0],free[1:]);q.compose(pre,inplace=True)
  sub=[]
  for p in selected:
   p=list(p);p.remove(a);p.remove(b);p.append(('v',free[0]));sub.append(p)
  rec(sub,free[1:]);q.compose(pre.inverse(),inplace=True);rec(rest,free)
 from collections import Counter
 rec(products,list(range(12,18)))
 return q
if __name__=='__main__':
 best=999999
 for seed in range(40):
  try:q=build(seed)
  except (ValueError,IndexError):continue
  q=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3,seed_transpiler=0)
  if q.depth()<best:
   best=q.depth();print(seed,best,q.count_ops(),flush=True)
   Path('artifacts/structured.qasm').write_text(qasm2.dumps(q))
