"""Reproducible checks on the claimed architecture-wide floor; no circuit search."""
import json,math,itertools
from pathlib import Path
from qiskit import QuantumCircuit,qasm2
import numpy as np
from post196_code_frontier import cells_of,supports_and_separations,complete
from two_stage_oracle import ROWCLS
out=Path('artifacts/post196_floor_audit')
q=qasm2.load('artifacts/196/two_stage_196.qasm');ops=dict(q.count_ops());slots=sum(len(i.qubits) for i in q.data)
r=dict(depth=q.depth(),gates=ops,wire_slots=slots,capacity=q.depth()*q.num_qubits,occupancy=slots/(q.depth()*q.num_qubits),occupancy_lower_bound=math.ceil(slots/q.num_qubits),slots_to_remove_for_depth99=slots-99*18)
# A diagonal with eight singleton parities disproves 3*T/n as a general bound.
p=QuantumCircuit(8)
for i in range(8):p.rz(.13*(i+1),i)
r['kernel_bound_counterexample']=dict(parity_terms=8,width=8,actual_depth=p.depth(),claimed_bound=3*8/8)
order,members=cells_of(ROWCLS,32);support,sep,pairs=supports_and_separations(order,members);full=(1<<len(pairs))-1
ranked=np.argsort(support)[:100];found=None
for a,b in itertools.combinations(map(int,ranked),2):
 got=complete(full&~(int(sep[a])|int(sep[b])),pairs,len(order))
 if got is None:continue
 options,free=got
 if not free:continue
 implemented=min(int(support[c]) for c in options)
 candidates=[base|sum((bits>>i&1)<<v for i,v in enumerate(free)) for base in options for bits in range(1<<len(free))]
 winner=min(candidates,key=lambda c:support[c]);exact=int(support[winner])
 if exact<implemented:
  found=dict(a=a,b=b,free=free,implemented_minimum=implemented,full_completion_minimum=exact,winner=winner,options=options);break
r['actual_row_completion_counterexample']=found
(out/'report.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
