from search import *
from qiskit.synthesis import synth_mcx_1_clean_kg24,synth_mcx_2_clean_kg24,synth_mcx_1_dirty_kg24,synth_mcx_2_dirty_kg24,synth_mcx_n_clean_m15,synth_mcx_n_dirty_i15,synth_mcx_noaux_v24,synth_mcx_noaux_hp24
from factor import phase_cube as old_phase_cube
@functools.lru_cache(None)
def best_mcz(vs,free):
 n=len(vs);dirty=tuple(v for v in range(18) if v not in vs)
 candidates=[]
 q=QuantumCircuit(18);old_phase_cube(q,frozenset(v+1 for v in vs),[v+1 for v in free]);candidates.append(q)
 if n>=4:
  options=[(synth_mcx_noaux_v24,()),(synth_mcx_noaux_hp24,()),(synth_mcx_1_dirty_kg24,dirty[:1]),(synth_mcx_2_dirty_kg24,dirty[:2])]
  if len(free)>=1:options.append((synth_mcx_1_clean_kg24,free[:1]))
  if len(free)>=2:options.append((synth_mcx_2_clean_kg24,free[:2]))
  if len(free)>=n-3:options.append((synth_mcx_n_clean_m15,free[:n-3]))
  if len(dirty)>=n-3:options.append((synth_mcx_n_dirty_i15,dirty[:n-3]))
  for fn,aux in options:
   try:
    sub=fn(n-1);q=QuantumCircuit(18);q.h(vs[-1]);q.compose(sub,list(vs)+list(aux),inplace=True);q.h(vs[-1]);candidates.append(q)
   except Exception:continue
 outs=[transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3) for q in candidates]
 return min(outs,key=lambda q:(q.depth(),q.count_ops().get('cx',0)))
def phase_cube(q,cube,free):
 vs=tuple(sorted(abs(v)-1 for v in cube));neg=[abs(v)-1 for v in cube if v<0]
 if neg:q.x(neg)
 q.compose(best_mcz(vs,tuple(v-1 for v in free)),inplace=True)
 if neg:q.x(neg)
