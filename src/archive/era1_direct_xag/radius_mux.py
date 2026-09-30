import radius_circuit as rc
from radius_circuit import *

def qrom_mux(seed=0):
 rng=random.Random(seed);base=list(range(6));rng.shuffle(base)
 shifts=rng.sample(range(1,6),2);orders=[base,base[shifts[0]:]+base[:shifts[0]],base[shifts[1]:]+base[:shifts[1]]]
 coefficients=[]
 for b,order in enumerate(orders):
  a=np.array([np.pi*((radius(sum(((k>>j)&1)<<v for j,v in enumerate(order)))>>b)&1) for k in range(64)])
  h=1
  while h<64:
   for i in range(0,64,2*h):
    lo=a[i:i+h].copy();hi=a[i+h:i+2*h].copy();a[i:i+h]=lo+hi;a[i+h:i+2*h]=lo-hi
   h*=2
  coefficients.append(a/64)
 q=QuantumCircuit(18)
 for j in range(64):
  for b in range(3):
   theta=coefficients[b][j^(j>>1)]
   if abs(theta)>1e-14:q.ry(float(theta),13+b)
  pos=((j+1)&-(j+1)).bit_length()-1 if j<63 else 5
  for b in range(3):q.cx(6+orders[b][pos],13+b)
 return q
rc.qrom=qrom_mux
if __name__=='__main__':
 best=999999
 for seed in range(200):
  q=rc.build(seed)
  if q.depth()<best:
   best=q.depth();print(seed,best,q.count_ops(),flush=True)
   Path('artifacts/radius_mux.qasm').write_text(qasm2.dumps(q));Path('artifacts/radius_mux_seed.json').write_text(str(seed))
