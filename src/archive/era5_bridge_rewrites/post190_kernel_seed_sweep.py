"""Compile the exact 8-wire 190 kernel with varied synthesis seeds."""
import json
from pathlib import Path
from qiskit import qasm2, transpile
from qiskit.quantum_info import Operator
from distributed_frame_search import materialize_output_layout, native
from build_two_stage_196 import encoders, KERNEL_WIRES

def equiv(a,b):
    x,y=Operator(a).data,Operator(b).data
    i,j=divmod(abs(x).argmax(),x.shape[1]); p=x[i,j]/y[i,j]
    return bool(max(abs(x-p*y).flat)<1e-8)

def run(out,seeds=32):
    assert not out.exists(); out.mkdir(parents=True)
    base=qasm2.load('artifacts/190/kernel.qasm'); enc=encoders(json.loads(Path('artifacts/190/class_codes.json').read_text()),298,506)
    rows=[]; best=(190,857)
    for seed in range(seeds):
        q=materialize_output_layout(transpile(base,basis_gates=['u3','cx'],qubits_initially_zero=False,
            optimization_level=3,seed_transpiler=seed))
        full=native(enc.compose(q,KERNEL_WIRES).compose(enc.inverse()))
        row=dict(seed=seed,kernel_depth=q.depth(),kernel_cx=q.count_ops().get('cx',0),
                 full_depth=full.depth(),full_cx=full.count_ops().get('cx',0),equiv=equiv(q,base))
        rows.append(row)
        if row['equiv'] and (row['full_depth'],row['full_cx'])<best:
            best=(row['full_depth'],row['full_cx']); p=out/f'oracle_d{best[0]}_cx{best[1]}.qasm';p.write_text(qasm2.dumps(full));row['path']=str(p);print('IMPROVEMENT',row,flush=True)
        if seed%4==0: print('seed',seed,'best',best,flush=True)
    (out/'report.json').write_text(json.dumps(dict(best=best,rows=rows),indent=2)+'\n'); print('done',best,flush=True)
if __name__=='__main__': run(Path('artifacts/post190_kernel_seed_v1'))
