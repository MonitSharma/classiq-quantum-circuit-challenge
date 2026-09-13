"""Bounded compiler-seed audit of the exact new baseline, preserving wire identity."""
import json
from pathlib import Path
from qiskit import qasm2,transpile
from distributed_frame_search import materialize_output_layout
from exhaustive_verify import exhaustive
out=Path('artifacts/post196_final_compile_v1');assert not out.exists();out.mkdir()
base=qasm2.load('artifacts/196/two_stage_196.qasm');rows=[];best=(196,858)
for seed in range(32):
 q=materialize_output_layout(transpile(base,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3,seed_transpiler=seed))
 score=(q.depth(),q.count_ops().get('cx',0));row=dict(seed=seed,depth=score[0],cx=score[1]);rows.append(row)
 if score<best:
  path=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';path.write_text(qasm2.dumps(q));exhaustive(path);row['path']=str(path);best=score;print('improvement',row,flush=True)
(out/'report.json').write_text(json.dumps(dict(best=best,rows=rows),indent=2));print('final compile audit',best,flush=True)
