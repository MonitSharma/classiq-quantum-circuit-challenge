from radius import *
from pair_search import pair_circuit
from qiskit.circuit.library import RC3XGate
from collections import Counter

def read_esop(path):
 cubes=[]
 for line in Path(path).read_text().splitlines():
  if not line or line[0] in '#.':continue
  pattern,outs=line.split()
  c=frozenset((i+7)*(1 if b=='1' else -1) for i,b in enumerate(pattern) if b!='-')
  mask=sum((b=='1')<<i for i,b in enumerate(outs));cubes.append((c,mask))
 return cubes

def out_basis(cubes):
 best=None;score=1e9
 for a,b,c in itertools.permutations(range(1,8),3):
  vals=[0,a,b,a^b,c,a^c,b^c,a^b^c]
  if len(set(vals))!=8:continue
  inv={v:i for i,v in enumerate(vals)}
  s=sum(inv[m].bit_count() for _,m in cubes)
  if s<score:best=((a,b,c),inv);score=s
 return best

def linear_output(q,cols,outs):
 # BFS over GL(3,2) to synthesize output transform with minimum CNOT count.
 from collections import deque
 initial=(1,2,4);target=tuple(sum(((cols[j]>>i)&1)<<j for j in range(3)) for i in range(3))
 que=deque([initial]);paths={initial:[]}
 while que:
  rows=que.popleft()
  if rows==target:
   for c,t in paths[rows]:q.cx(outs[c],outs[t])
   return
  for c,t in itertools.permutations(range(3),2):
   nr=list(rows);nr[t]^=nr[c];nr=tuple(nr)
   if nr not in paths:paths[nr]=paths[rows]+[(c,t)];que.append(nr)

def toggle_outputs(q,controls,mask,outs,free):
 chosen=[outs[i] for i in range(3) if mask>>i&1]
 t=chosen[0];cs=sorted(abs(v)-1 for v in controls);neg=[abs(v)-1 for v in controls if v<0]
 for other in chosen[1:]:q.cx(t,other)
 if neg:q.x(neg)
 if len(cs)==0:q.x(t)
 elif len(cs)==1:q.cx(cs[0],t)
 elif len(cs)==2:q.rccx(*cs,t)
 elif len(cs)==3:q.append(RC3XGate(),cs+[t])
 else:balanced(q,cs,t,list(free))
 if neg:q.x(neg)
 for other in chosen[1:]:q.cx(t,other)

def balanced(q,cs,t,free):
 if len(cs)==1:q.cx(cs[0],t)
 elif len(cs)==2:q.rccx(*cs,t)
 elif len(cs)==3:q.append(RC3XGate(),cs+[t])
 else:
  a=free[0];pre=QuantumCircuit(18);pre.append(RC3XGate(),cs[:3]+[a])
  q.compose(pre,inplace=True);balanced(q,[a]+cs[3:],t,free[1:]);q.compose(pre.inverse(),inplace=True)

def qrom(seed=0):
 cubes=read_esop('experiments/radius.esop');cols,inv=out_basis(cubes);cubes=[(c,inv[m]) for c,m in cubes]
 rng=random.Random(seed);q=QuantumCircuit(18);outs=[13,14,15]
 def rec(cubes,free):
  if not cubes:return
  # emit short products immediately
  remaining=[]
  for c,m in cubes:
   if len(c)<=2:toggle_outputs(q,c,m,outs,free)
   else:remaining.append((c,m))
  if not remaining:return
  counts=Counter(pair for c,m in remaining for pair in itertools.combinations(sorted(c),2))
  repeated=[((k-1)*rng.uniform(.5,1.5),p) for p,k in counts.items() if k>=2]
  if not free or not repeated:
   rng.shuffle(remaining)
   for c,m in remaining:toggle_outputs(q,c,m,outs,free)
   return
  _,pair=max(repeated);target=free[0];pre=QuantumCircuit(18);neg=[abs(v)-1 for v in pair if v<0]
  if neg:pre.x(neg)
  pre.rccx(*(abs(v)-1 for v in pair),target)
  if neg:pre.x(neg)
  q.compose(pre,inplace=True)
  covered=[(frozenset(c-set(pair))|{target+1},m) for c,m in remaining if set(pair)<=c]
  rec(covered,free[1:]);q.compose(pre.inverse(),inplace=True)
  rec([(c,m) for c,m in remaining if not(set(pair)<=c)],free)
 rec(cubes,[12,16,17]);linear_output(q,cols,outs)
 return q

def main_disk(seed=0):
 q=qrom(seed);undo=q.inverse();r=[13,14,15]
 # Reversible x reflection maps both circle centres to low coordinate 8.
 fold=QuantumCircuit(18)
 for b in range(4):fold.cx(11,b)
 fold.x(3)
 for b in range(3):fold.cx(3,b)
 fold.x(3)
 q.compose(fold,inplace=True)
 guard=QuantumCircuit(18)
 guard.cx(11,4);guard.x(4);guard.rccx(5,4,12);guard.x(4);guard.cx(11,4)
 guard.x([14,15]);guard.rccx(14,15,16);guard.x(16);guard.x([14,15])
 guard.rccx(12,16,17)
 q.compose(guard,inplace=True)
 compare=QuantumCircuit(18);compare.x([0,1,2]);carry=3
 for i in range(3):
  compare.cx(r[i],i);compare.cx(r[i],carry);compare.rccx(carry,i,r[i]);carry=r[i]
 q.compose(compare,inplace=True);q.cz(17,15);q.compose(compare.inverse(),inplace=True)
 q.compose(guard.inverse(),inplace=True);q.compose(fold.inverse(),inplace=True);q.compose(undo,inplace=True)
 return q

def build(seed=0):
 q=main_disk(seed)
 for x,y in [(truth(range(2,27)),truth(range(29,54))),(truth(range(27,49)),truth(range(39,44))),(truth([32,48]),truth(range(17,22)))]:
  q.compose(pair_circuit(x,y),inplace=True)
 return transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)

if __name__=='__main__':
 best=99999
 for seed in range(100):
  try:q=build(seed)
  except (ValueError,IndexError):continue
  if q.depth()<best:
   best=q.depth();print(seed,best,q.count_ops(),flush=True)
   Path('artifacts/radius.qasm').write_text(qasm2.dumps(q));Path('artifacts/radius_seed.json').write_text(str(seed))
