from search import *
from pebble import smart_compute
from formula import formula,remap

def compile_stream(terms,order,mode='esop'):
 q=QuantumCircuit(18);undo=QuantumCircuit(18);px=py=0
 for i in order:
  x,y=terms[i];a=QuantumCircuit(18);b=QuantumCircuit(18)
  if mode=='esop':
   a=pred(x^px,0,12,[14,15,16,17]);b=pred(y^py,6,13,[14,15,16,17])
  else:
   smart_compute(a,remap(formula(x^px,6),range(6)),12,[14,15,16,17]);smart_compute(b,remap(formula(y^py,6),range(6,12)),13,[14,15,16,17])
  q.compose(a,inplace=True);q.compose(b,inplace=True);undo.compose(a,inplace=True);undo.compose(b,inplace=True)
  q.cz(12,13);px=x;py=y
 q.compose(undo.inverse(),inplace=True)
 return q

def order_cost(terms,order):
 px=py=0;s=0
 for i in order:
  x,y=terms[i]
  s+=sum(sum(max(0,2*m.bit_count()-3) for m,v in esop(t,6)) for t in [x^px,y^py]);px=x;py=y
 return s

if __name__=='__main__':
 best=999999
 for terms in [nested_terms(),row_terms()]:
  order=list(range(len(terms)));cost=order_cost(terms,order)
  for j in range(100):
   rng=random.Random(j);candidate=order.copy();rng.shuffle(candidate)
   c=order_cost(terms,candidate)
   if c<cost:order=candidate;cost=c
   if j%5==0:
    for mode in ['esop','formula']:
     q=compile_stream(terms,order,mode)
     qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3,seed_transpiler=j)
     if qc.depth()<best:
      best=qc.depth();print(j,mode,best,qc.count_ops(),flush=True)
      Path('artifacts/stream.qasm').write_text(qasm2.dumps(qc));Path('artifacts/stream_config.json').write_text(json.dumps([terms,order,mode]))
