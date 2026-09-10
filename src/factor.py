from search import *
from collections import Counter

# signed literals 1..12 and -1..-12; ancilla literals 13..18

def cubes_from_terms(terms):
 out=set()
 for x,y in terms:
  for mx,vx in esop(x,6):
   for my,vy in esop(y,6):
    cube=frozenset((i+1 if v>>i&1 else -i-1)+offset*(1 if v>>i&1 else -1) for m,v,offset in [(mx,vx,0),(my,vy,6)] for i in range(6) if m>>i&1)
    if cube in out:out.remove(cube)
    else:out.add(cube)
 return out

def simplify(cubes):
 cubes=set(cubes)
 while True:
  done=False
  for c in sorted(cubes,key=lambda x:(len(x),tuple(sorted(x)))):
   for lit in c:
    other=(c-{lit})|{-lit}
    if other in cubes:
     cubes.remove(c);cubes.remove(other);new=c-{lit}
     if new in cubes:cubes.remove(new)
     else:cubes.add(new)
     done=True;break
    other=c-{lit}
    if other in cubes:
     cubes.remove(c);cubes.remove(other);new=other|{-lit}
     if new in cubes:cubes.remove(new)
     else:cubes.add(new)
     done=True;break
   if done:break
  if not done:return cubes

def cnots(q,ls):
 negs=[abs(l)-1 for l in ls if l<0]
 if negs:q.x(negs)
 return negs

def phase_cube(q,cube,free):
 ls=sorted(cube,key=abs);ng=cnots(q,ls);vs=[abs(l)-1 for l in ls]
 if len(vs)==0:q.global_phase+=np.pi
 elif len(vs)==1:q.z(vs[0])
 elif len(vs)==2:q.cz(*vs)
 elif len(vs)==3:q.h(vs[-1]);q.ccx(*vs);q.h(vs[-1])
 elif len(free)<len(vs)-2:
  q.h(vs[-1]);q.mcx(vs[:-1],vs[-1]);q.h(vs[-1])
 else:
  pre=QuantumCircuit(18)
  # compute all except last into tree
  pool=list(vs[:-1]);temp=[]
  while len(pool)>1:
   a,b=pool.pop(0),pool.pop(0)
   t=free[len(temp)]-1;pre.rccx(a,b,t);temp.append(t);pool.append(t)
  q.compose(pre,inplace=True);q.cz(pool[0],vs[-1]);q.compose(pre.inverse(),inplace=True)
 if ng:q.x(ng)

def synth(cubes,seed=0):
 rng=random.Random(seed);q=QuantumCircuit(18)
 def rec(cubes,free):
  cubes=simplify(cubes)
  small=[c for c in cubes if len(c)<=2]
  rng.shuffle(small)
  for c in small:phase_cube(q,c,free);cubes.remove(c)
  if not cubes:return
  pairs=Counter(pair for c in cubes for pair in itertools.combinations(sorted(c),2))
  if not free:
   # any nontrivial remaining triple can be applied without workspace
   for c in sorted(cubes,key=len):
    phase_cube(q,c,free)
   return
  # choose a common factor; reserve free workspace for deepest individual cube
  options=[]
  for pair,num in pairs.items():
   covered=[c for c in cubes if set(pair)<=c]
   score=(num-1)*2+sum(len(c)-2 for c in covered)*.15
   if seed:score*=rng.uniform(.6,1.4)
   options.append((score,pair,covered))
  _,pair,covered=max(options,key=lambda x:x[0])
  rest=cubes-set(covered)
  target=free[0];remaining=free[1:]
  pre=QuantumCircuit(18);ng=cnots(pre,pair);pre.rccx(*(abs(v)-1 for v in pair),target-1)
  if ng:pre.x(ng)
  q.compose(pre,inplace=True)
  rec({frozenset(c-set(pair))|{target} for c in covered},remaining)
  q.compose(pre.inverse(),inplace=True)
  rec(rest,free)
 rec(cubes,list(range(13,19)))
 return q

def fixed_esop(order):
 # reorder bit axes so recursion removes MSB, preserving one fixed variable order.
 tt=np.array([int(MASK[y,x]) for y in range(64) for x in range(64)],dtype=np.uint8)
 indices=np.array([sum(((j>>k)&1)<<b for k,b in enumerate(order)) for j in range(4096)])
 tt=tt[indices]
 @functools.lru_cache(None)
 def go(t):
  n=(len(t)).bit_length()-1
  if not any(t):return ()
  if all(t):return (frozenset(),)
  half=len(t)//2;lo=t[:half];hi=t[half:];delta=bytes(a^b for a,b in zip(lo,hi));v=order[n-1]+1
  a=go(lo);b=go(hi);d=go(delta)
  opts=[tuple(c|{-v} for c in a)+tuple(c|{v} for c in b),a+tuple(c|{v} for c in d),b+tuple(c|{-v} for c in d)]
  return min(opts,key=lambda cs:sum(max(1,len(c)-1) for c in cs))
 return simplify(go(bytes(tt)))

if __name__=='__main__':
 best=999999
 for i in range(300):
  if i==0:cubes=cubes_from_terms(nested_terms())
  elif i==1:cubes=cubes_from_terms(row_terms())
  else:
   order=list(range(12));random.Random(i).shuffle(order)
   cubes=fixed_esop(order)
  try:q=synth(cubes,i)
  except ValueError:continue
  qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3,seed_transpiler=0)
  if qc.depth()<best:
   best=qc.depth();print(i,'best',best,'cx',qc.count_ops().get('cx'), 'cubes',len(cubes),flush=True)
   Path('artifacts/factor.qasm').write_text(qasm2.dumps(qc))
   Path('artifacts/factor_cubes.json').write_text(json.dumps([list(c) for c in cubes]))
   Path('artifacts/factor_seed.json').write_text(json.dumps(i))
