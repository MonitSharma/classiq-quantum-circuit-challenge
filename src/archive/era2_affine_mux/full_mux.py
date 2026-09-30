from radius import *
from mcz import phase_cube
from pair_search import pair_circuit

def multiplexer(tables,outputs,controls,axis,seed=0):
 n=len(controls);N=1<<n;rng=random.Random(seed);base=list(range(n));rng.shuffle(base)
 shifts=list(range(n));rng.shuffle(shifts);orders=[base[s:]+base[:s] for s in shifts[:len(tables)]]
 co=[]
 for table,order in zip(tables,orders):
  a=np.array([np.pi*((table>>sum(((k>>j)&1)<<v for j,v in enumerate(order)))&1) for k in range(N)])
  h=1
  while h<N:
   for i in range(0,N,2*h):
    lo=a[i:i+h].copy();hi=a[i+h:i+2*h].copy();a[i:i+h]=lo+hi;a[i+h:i+2*h]=lo-hi
   h*=2
  co.append(a/N)
 q=QuantumCircuit(18)
 for j in range(N):
  for b,t in enumerate(outputs):
   angle=float(co[b][j^(j>>1)])
   if abs(angle)>1e-14:
    if axis=='y':q.ry(angle,t)
    else:q.rz(angle,t)
  pos=((j+1)&-(j+1)).bit_length()-1 if j<N-1 else n-1
  for b,t in enumerate(outputs):q.cx(controls[orders[b][pos]],t)
 return q

def build(seed=0):
 a=truth(range(29,54));b=truth(range(39,44));v=truth(y for y in range(64) if radius(y)>0)
 lookup=multiplexer(R+[a,b,v],list(range(12,18)),list(range(6,12)),'y',seed)
 q=lookup.copy()
 xs=truth(range(2,27));xb=truth(range(27,49));xo=((1<<64)-1)^xs^xb
 q.cx(17,15);q.cx(17,16)
 left=multiplexer([xs,xb,xo],[15,16,17],list(range(6)),'z',seed+10000)
 q.compose(left,inplace=True);q.z(17);q.cx(17,16);q.cx(17,15)
 fold=QuantumCircuit(18)
 for k in range(4):fold.cx(11,k)
 fold.x(3)
 for k in range(3):fold.cx(3,k)
 fold.x(3);q.compose(fold,inplace=True)
 comp=QuantumCircuit(18);comp.x([0,1,2]);carry=3
 for i in range(3):
  comp.cx(12+i,i);comp.cx(12+i,carry);comp.rccx(carry,i,12+i);carry=12+i
 q.compose(comp,inplace=True)
 q.cx(11,4);q.x(4)
 phase_cube(q,frozenset([18,6,5,15]),[]) # valid, x5, transformed x4, comparison carry
 q.x(4);q.cx(11,4)
 q.compose(comp.inverse(),inplace=True);q.compose(fold.inverse(),inplace=True)
 q.compose(lookup.inverse(),inplace=True)
 q.compose(pair_circuit(truth([32,48]),truth(range(17,22))),inplace=True)
 return transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)

if __name__=='__main__':
 best=999999
 for seed in range(200):
  q=build(seed)
  if q.depth()<best:
   best=q.depth();print(seed,best,q.count_ops(),flush=True)
   Path('artifacts/full_mux.qasm').write_text(qasm2.dumps(q));Path('artifacts/full_mux_seed.json').write_text(str(seed))
