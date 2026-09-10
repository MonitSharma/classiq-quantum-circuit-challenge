import functools, itertools, json, random, time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, transpile, qasm2

def logo(x,y):
 return (2<=x<=26 and 29<=y<=53) or (26<=x<=49 and 39<=y<=43) or (x-55)**2+(y-41)**2<=42 or (x-40)**2+(y-19)**2<=72
MASK=np.array([[logo(x,y) for x in range(64)] for y in range(64)],dtype=np.uint8)

def truth(vals): return sum(1<<int(v) for v in vals)

def cof(t,n,b,val):
 return sum(((t>>((i&((1<<b)-1))|((i>>b)<<(b+1))|(val<<b)))&1)<<i for i in range(1<<(n-1)))

@functools.lru_cache(None)
def esop(t,n):
 if t==0:return ()
 if t==(1<<(1<<n))-1:return ((0,0),)
 best=None;score=1e9
 for b in range(n):
  lo=cof(t,n,b,0);hi=cof(t,n,b,1)
  for mode,a,c in [(0,lo,hi),(1,lo,lo^hi),(2,hi,lo^hi)]:
   aa=esop(a,n-1);cc=esop(c,n-1)
   def lift(cubes,v):
    out=[]
    for mask,value in cubes:
     mask=(mask&((1<<b)-1))|((mask>>b)<<(b+1))
     value=(value&((1<<b)-1))|((value>>b)<<(b+1))
     if v is not None:mask|=1<<b;value|=v<<b
     out.append((mask,value))
    return out
   cubes=tuple(lift(aa,0 if mode==0 else None)+lift(cc,1 if mode!=2 else 0))
   s=sum(1+2*max(0,m.bit_count()-1) for m,v in cubes)
   if s<score:score=s;best=cubes
 return best

def mcxr(q,controls,target,scratch):
 # Relative-phase compute; used only with the exact inverse enclosing diagonal action.
 if not controls:q.x(target)
 elif len(controls)==1:q.cx(controls[0],target)
 elif len(controls)==2:q.rccx(*controls,target)
 else:
  pre=QuantumCircuit(18)
  pre.rccx(controls[0],controls[1],scratch[0])
  for i,c in enumerate(controls[2:-1]):pre.rccx(scratch[i],c,scratch[i+1])
  q.compose(pre,inplace=True)
  q.rccx(scratch[len(controls)-3],controls[-1],target)
  q.compose(pre.inverse(),inplace=True)

def pred(t,offset,target,scratch):
 q=QuantumCircuit(18)
 for mask,val in esop(t,6):
  cs=[offset+i for i in range(6) if mask>>i&1];neg=[offset+i for i in range(6) if (mask>>i&1) and not (val>>i&1)]
  q.x(neg) if neg else None
  mcxr(q,cs,target,scratch)
  q.x(neg) if neg else None
 return q

def row_terms():
 groups={}
 for y,row in enumerate(MASK):
  t=truth(np.where(row)[0]);groups.setdefault(t,[]).append(y)
 return [(x,truth(ys)) for x,ys in groups.items() if x]

def nested_terms():
 # Exact XOR telescoping of nested intervals for each isolated disk.
 terms=[]
 terms.append((truth(range(2,27)),truth(range(29,54))))
 # bar excludes shared x=26 and disk starts at x=49 on these rows
 terms.append((truth(range(27,49)),truth(range(39,44))))
 for cx,cy,r in [(55,41,42),(40,19,72)]:
  groups={}
  for y in range(64):
   xs=truth(x for x in range(64) if (x-cx)**2+(y-cy)**2<=r)
   if xs:groups.setdefault(xs,[]).append(y)
  old=0
  for xs,ys in sorted(groups.items(),key=lambda kv:kv[0].bit_count()):
   terms.append((xs^old,truth(y for y in range(min(ys),max(ys)+1))))
   old=xs
 return terms

def compile_terms(terms,seed=0):
 q=QuantumCircuit(18)
 for x,y in terms:
  a=pred(x,0,12,[14,15,16,17]);b=pred(y,6,13,[14,15,16,17])
  q.compose(a,inplace=True);q.compose(b,inplace=True);q.cz(12,13)
  q.compose(b.inverse(),inplace=True);q.compose(a.inverse(),inplace=True)
 return transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3,seed_transpiler=seed)

def check_terms(terms):
 out=np.zeros((64,64),dtype=np.uint8)
 for x,y in terms:
  out ^= np.outer([(y>>i)&1 for i in range(64)],[(x>>i)&1 for i in range(64)]).astype(np.uint8)
 assert np.array_equal(out,MASK)

if __name__=='__main__':
 for name,terms in [('rows',row_terms()),('nested',nested_terms())]:
  check_terms(terms)
  print(name,len(terms),[(len(esop(x,6)),len(esop(y,6))) for x,y in terms],flush=True)
  q=compile_terms(terms)
  print(name,q.depth(),q.count_ops(),flush=True)
  Path('artifacts/'+name+'.qasm').write_text(qasm2.dumps(q))
  Path('artifacts/'+name+'_terms.json').write_text(json.dumps(terms))
