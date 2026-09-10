from xag_phase import *
from qiskit_aer import AerSimulator
from qiskit import transpile
import mcz
import xag_phase
xag_phase.phase_cube=mcz.phase_cube
backend=AerSimulator(method='statevector',max_parallel_threads=2)
ts=json.loads(Path('artifacts/pair_terms.json').read_text())
for ti,pair in enumerate(ts):
 g,rr=make_graph([pair])
 for ai,fs in enumerate(alternatives(g,rr[0],maxf=5)):
  try:path=plan(g,frozenset(),fs,max_states=10000)
  except ValueError:continue
  q=make_one(g,fs,path)
  test=QuantumCircuit(18);test.h(range(12));test.compose(q,inplace=True)
  test=transpile(test,basis_gates=['u3','cx'],qubits_initially_zero=False);test.save_statevector()
  v=np.asarray(backend.run(test).result().get_statevector())[:4096]*64
  target=np.array([-1 if (pair[0]>>x&1) and (pair[1]>>y&1) else 1 for y in range(64) for x in range(64)])
  phase=v[0]/target[0];err=np.max(np.abs(v-phase*target))
  if err>1e-8:
   print('BAD',ti,ai,'forms',fs,'path',path,'err',err,flush=True)
   # Verify affine phase precondition independently on arbitrary physical bits.
   wire={i:i for i in range(12)};live=set();free=list(range(12,18))
   from static_cache import apply_path
   prep=QuantumCircuit(18);apply_path(prep,g,path,wire,free,live)
   pre,pivots=linear_many(fs,wire);bits=np.arange(1<<18,dtype=np.uint32);orig=bits.copy()
   if pre is not None:
    for inst in pre.data:
     qs=[pre.find_bit(v).index for v in inst.qubits]
     if inst.operation.name=='x':bits^=1<<qs[0]
     else:bits^=((bits>>qs[0])&1)<<qs[1]
    actual=np.ones(len(bits),np.uint8)
    for p in pivots:actual&=(bits>>p)&1
   else:actual=np.zeros(len(bits),np.uint8)
   expected=np.ones(len(bits),np.uint8)
   for f in fs:
    fval=np.full(len(bits),int(-1 in f),np.uint8)
    for u in f:
     if u!=-1:fval^=(orig>>wire[u])&1
    expected&=fval
   print('linear errors',np.count_nonzero(expected!=actual),'pivots',pivots,'free',free,flush=True)
   raise SystemExit()
 print('term okay',ti,flush=True)
