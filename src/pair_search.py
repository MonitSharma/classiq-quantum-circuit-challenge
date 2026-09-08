from xag_phase import *
import mcz
import xag_phase
xag_phase.phase_cube=mcz.phase_cube
# Per-pair graphs avoid introducing dependencies on previous predicates.
CACHE={}

def pair_circuit(x,y):
 key=(x,y)
 if key in CACHE:return CACHE[key]
 g,rs=make_graph([(x,y)]);best=None;bs=1e9
 for fs in alternatives(g,rs[0],maxf=5):
  try:path=plan(g,frozenset(),fs,max_states=10000)
  except ValueError:continue
  q=make_one(g,fs,path)
  qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
  sc=qc.depth()
  if sc<bs:bs=sc;best=qc
 if best is None:raise ValueError('pair')
 CACHE[key]=best
 return best

def circuit(ts):
 q=QuantumCircuit(18)
 for x,y in ts:q.compose(pair_circuit(x,y),inplace=True)
 qc=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
 return min([q,qc],key=lambda a:a.depth())

if __name__=='__main__':
 ts=json.loads(Path('artifacts/rank_terms.json').read_text());rng=random.Random(6281)
 curr=ts.copy();s=sum(pair_circuit(x,y).depth() for x,y in curr);best=s
 q=circuit(curr);print('initial',s,q.depth(),q.count_ops(),flush=True)
 Path('artifacts/pair.qasm').write_text(qasm2.dumps(q));Path('artifacts/pair_terms.json').write_text(json.dumps(curr))
 bestdepth=q.depth()
 for step in range(300):
  i,j=rng.sample(range(len(curr)),2);xi,yi=curr[i];xj,yj=curr[j];cand=curr.copy()
  cand[i]=(xi^xj,yi);cand[j]=(xj,yi^yj)
  try:delta=sum(pair_circuit(*cand[k]).depth()-pair_circuit(*curr[k]).depth() for k in [i,j])
  except ValueError:continue
  temp=max(1,10*(1-step/300))
  if delta<0 or rng.random()<np.exp(-delta/temp):curr=cand;s+=delta
  if s<best:
   best=s;q=circuit(curr);print(step,s,q.depth(),q.count_ops(),flush=True)
   if q.depth()<bestdepth:
    bestdepth=q.depth();Path('artifacts/pair.qasm').write_text(qasm2.dumps(q));Path('artifacts/pair_terms.json').write_text(json.dumps(curr))
  if step%25==0:print('progress',step,'cached',len(CACHE),flush=True)
