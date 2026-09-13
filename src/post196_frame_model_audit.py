"""A fixed-frame contention counterexample to the scalar 'exact' cost model."""
import json,math
from pathlib import Path
from qiskit import QuantumCircuit
from post196_frame_balance import TOUR
subset=3;hosts=6
model=max(2+TOUR[subset],math.ceil(hosts*TOUR[subset]/3))
q=QuantumCircuit(9)
for i in range(3,9):q.rz(.13*(i+1),i)
for i in range(3,9):q.cx(0,i);q.rz(.17*(i+1),i)
for i in range(3,9):q.cx(0,i)
row=dict(subsets=[subset]*hosts,model=model,mandatory_cx_on_low_wire0=12,example_depth=q.depth(),gl6_size=math.prod(64-2**i for i in range(6)))
assert model==4 and q.depth()==13
Path('artifacts/post196_frame_model_audit/report.json').write_text(json.dumps(row,indent=2));print(row)
