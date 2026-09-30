from search import *
# Expressions: constants ints; ('v', bit), ('not', a), ('xor', a,b), ('and',a,b)
def Not(a):
 if isinstance(a,int):return 1-a
 if a[0]=='not':return a[1]
 return ('not',a)
def Xor(a,b):
 if a==0:return b
 if b==0:return a
 if a==1:return Not(b)
 if b==1:return Not(a)
 if a==b:return 0
 return ('xor',a,b)
def And(a,b):
 if a==0 or b==0:return 0
 if a==1:return b
 if b==1:return a
 if a==b:return a
 return ('and',a,b)
def cost(a):
 if isinstance(a,int) or a[0]=='v':return 0
 if a[0]=='not':return cost(a[1])
 return (1 if a[0]=='and' else 0)+cost(a[1])+cost(a[2])
def size(a):
 if isinstance(a,int) or a[0]=='v':return 0
 return 1+sum(size(x) for x in a[1:])
def remap(a,vs):
 if isinstance(a,int):return a
 if a[0]=='v':return ('v',vs[a[1]])
 return (a[0],*(remap(x,vs) for x in a[1:]))

@functools.lru_cache(None)
def formula(t,n):
 full=(1<<(1<<n))-1
 if t==0:return 0
 if t==full:return 1
 # remove irrelevant variables first
 for b in range(n):
  lo=cof(t,n,b,0);hi=cof(t,n,b,1)
  if lo==hi:return remap(formula(lo,n-1),[i for i in range(n) if i!=b])
 if n==1:return ('v',0) if t==2 else Not(('v',0))
 best=None;score=(1e9,1e9)
 def put(a):
  nonlocal best,score
  s=(cost(a),size(a))
  if s<score:best=a;score=s
 # disjoint-support AND, OR and XOR decompositions
 vals=np.array([(t>>i)&1 for i in range(1<<n)],dtype=np.uint8)
 for mask in range(1,1<<(n-1)):
  aa=[i for i in range(n) if mask>>i&1];bb=[i for i in range(n) if not mask>>i&1]
  ai=[sum(((j>>k)&1)<<v for k,v in enumerate(aa)) for j in range(1<<len(aa))]
  bi=[sum(((j>>k)&1)<<v for k,v in enumerate(bb)) for j in range(1<<len(bb))]
  mat=vals[np.array(ai)[:,None]+np.array(bi)[None,:]]
  if np.array_equal(mat,mat[:,0,None]^mat[0,None,:]^mat[0,0]):
   a=remap(formula(truth(np.where(mat[:,0])[0]),len(aa)),aa)
   b=remap(formula(truth(np.where(mat[0,:]^mat[0,0])[0]),len(bb)),bb)
   put(Xor(a,b))
  for invert in [False,True]:
   m=1-mat if invert else mat
   a=m.max(axis=1);b=m.max(axis=0)
   if np.array_equal(m,a[:,None]*b[None,:]):
    a=remap(formula(truth(np.where(a)[0]),len(aa)),aa)
    b=remap(formula(truth(np.where(b)[0]),len(bb)),bb)
    z=And(a,b);put(Not(z) if invert else z)
 if best is not None:return best
 for b in range(n):
  lo=cof(t,n,b,0);hi=cof(t,n,b,1)
  vs=[i for i in range(n) if i!=b];v=('v',b)
  a=remap(formula(lo,n-1),vs);h=remap(formula(hi,n-1),vs);d=remap(formula(lo^hi,n-1),vs)
  put(Xor(a,And(v,d)));put(Xor(h,And(Not(v),d)))
  put(Xor(And(Not(v),a),And(v,h)))
 return best

def literal(e):
 return not isinstance(e,int) and (e[0]=='v' or (e[0]=='not' and e[1][0]=='v'))
def var(e):return e[1] if e[0]=='v' else e[1][1]
def neg(e):return e[0]=='not'

def compute(q,e,target,scratch):
 if e==0:return
 if e==1:q.x(target);return
 if e[0]=='v':q.cx(e[1],target);return
 if e[0]=='not':compute(q,e[1],target,scratch);q.x(target);return
 if e[0]=='xor':
  compute(q,e[1],target,scratch);compute(q,e[2],target,scratch);return
 a,b=e[1:];stack=[];cs=[];remaining=list(scratch)
 # harder child first
 if cost(a)<cost(b):a,b=b,a
 for child in (a,b):
  if literal(child):
   v=var(child)
   pre=QuantumCircuit(18)
   if neg(child):pre.x(v)
  else:
   if not remaining:raise ValueError('scratch')
   v=remaining.pop(0);pre=QuantumCircuit(18)
   compute(pre,child,v,remaining)
  q.compose(pre,inplace=True);stack.append(pre);cs.append(v)
 q.rccx(*cs,target)
 for pre in reversed(stack):q.compose(pre.inverse(),inplace=True)

def compile_formulas(terms,seed=0):
 q=QuantumCircuit(18)
 for x,y in terms:
  a=remap(formula(x,6),list(range(6)))
  b=remap(formula(y,6),list(range(6,12)))
  pre=QuantumCircuit(18)
  compute(pre,a,12,[14,15,16,17]);compute(pre,b,13,[14,15,16,17])
  q.compose(pre,inplace=True);q.cz(12,13);q.compose(pre.inverse(),inplace=True)
 return transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3,seed_transpiler=seed)
if __name__=='__main__':
 for name,terms in [('rows',row_terms()),('nested',nested_terms())]:
  print(name,[(cost(formula(x,6)),cost(formula(y,6))) for x,y in terms],flush=True)
  q=compile_formulas(terms)
  print(name,q.depth(),q.count_ops(),flush=True)
  Path('artifacts/'+name+'_formula.qasm').write_text(qasm2.dumps(q))
