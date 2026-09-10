from pair_search import *
from qiskit.circuit.library import RC3XGate
MASK64=(1<<64)-1

def rot(t,s):return ((t<<s)|(t>>(64-s)))&MASK64 if s else t

def add(q,offset,s):
 # A basis permutation up to phases, paired with its exact inverse around the oracle.
 for bit in range(6):
  if not(s>>bit&1):continue
  for k in range(5,bit,-1):
   controls=list(range(offset+bit,offset+k));t=offset+k
   if len(controls)==3:q.append(RC3XGate(),controls+[t])
   else:mcxr(q,controls,t,list(range(12,18)))
  q.x(offset+bit)

def transform_circuit(ts,sx,sy):
 transformed=[(rot(x,sx),rot(y,sy)) for x,y in ts]
 q=QuantumCircuit(18);add(q,0,sx);add(q,6,sy);undo=q.inverse()
 for x,y in transformed:q.compose(pair_circuit(x,y),inplace=True)
 q.compose(undo,inplace=True);qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
 return min([q,qc],key=lambda q:q.depth()),transformed

if __name__=='__main__':
 ts=json.loads(Path('artifacts/pair_terms.json').read_text())
 shiftlists=[]
 for axis in [0,1]:
  ranked=[]
  for s in range(64):
   q=QuantumCircuit(18);add(q,axis*6,s);extra=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3).depth()*2
   c=sum(cost(formula(rot(p[axis],s),6)) for p in ts)
   ranked.append((c*10+extra,s,c,extra))
  ranked.sort();print('axis',axis,'shifts',ranked[:12],flush=True);shiftlists.append([r[1] for r in ranked[:6]])
 best=99999
 for sx,sy in itertools.product(*shiftlists):
  q,tt=transform_circuit(ts,sx,sy)
  if q.depth()<best:
   best=q.depth();print('best',sx,sy,best,q.count_ops(),flush=True)
   Path('artifacts/translated.qasm').write_text(qasm2.dumps(q));Path('artifacts/translated_config.json').write_text(json.dumps([ts,sx,sy]))
