from formula import *

def dirty(q,e,free):
 if literal(e):
  v=var(e)
  if neg(e):q.x(v)
  return v,[]
 if not free:raise ValueError('scratch')
 target=free[0];remaining=free[1:]
 if e==0:return target,[target]
 if e==1:q.x(target);return target,[target]
 if e[0]=='not':
  v,used=dirty(q,e[1],free);q.x(v);return v,used
 if e[0]=='xor':
  # accumulate subexpressions cleanly in target; retain target only
  smart_compute(q,e[1],target,remaining);smart_compute(q,e[2],target,remaining)
  return target,[target]
 a,b=e[1:]
 if cost(a)<cost(b):a,b=b,a
 v,used=dirty(q,a,remaining)
 rest=[w for w in remaining if w not in used]
 w,used2=dirty(q,b,rest)
 if v==w:raise ValueError('same')
 q.rccx(v,w,target)
 return target,[target]+used+used2

def smart_compute(q,e,target,scratch):
 if isinstance(e,int):
  if e:q.x(target)
  return
 if e[0]=='v':q.cx(e[1],target);return
 if e[0]=='not':smart_compute(q,e[1],target,scratch);q.x(target);return
 if e[0]=='xor':smart_compute(q,e[1],target,scratch);smart_compute(q,e[2],target,scratch);return
 a,b=e[1:]
 if cost(a)<cost(b):a,b=b,a
 for mode in [0,1,2]:
  try:
   pre=QuantumCircuit(18)
   if mode==0:
    v,used=dirty(pre,a,list(scratch));w,used2=dirty(pre,b,[z for z in scratch if z not in used])
   else:
    if literal(a):
     v=var(a);used=[]
     if neg(a):pre.x(v)
    else:
     v=scratch[0];used=[v];smart_compute(pre,a,v,scratch[1:])
    rest=[z for z in scratch if z not in used]
    if mode==1:w,used2=dirty(pre,b,rest)
    elif literal(b):
     w=var(b)
     if neg(b):pre.x(w)
    else:
     w=rest[0];smart_compute(pre,b,w,rest[1:])
   if v==w:raise ValueError('same')
   q.compose(pre,inplace=True);q.rccx(v,w,target);q.compose(pre.inverse(),inplace=True);return
  except (ValueError,IndexError):continue
 raise ValueError('scratch')

def compile_smart(terms,seed=0):
 q=QuantumCircuit(18)
 for x,y in terms:
  a=remap(formula(x,6),list(range(6)));b=remap(formula(y,6),list(range(6,12)))
  pre=QuantumCircuit(18)
  smart_compute(pre,a,12,[14,15,16,17]);smart_compute(pre,b,13,[14,15,16,17])
  q.compose(pre,inplace=True);q.cz(12,13);q.compose(pre.inverse(),inplace=True)
 return transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3,seed_transpiler=seed)
if __name__=='__main__':
 for name,terms in [('rows',row_terms()),('nested',nested_terms())]:
  q=compile_smart(terms)
  print(name,q.depth(),q.count_ops(),flush=True)
  Path('artifacts/'+name+'_smart.qasm').write_text(qasm2.dumps(q))
