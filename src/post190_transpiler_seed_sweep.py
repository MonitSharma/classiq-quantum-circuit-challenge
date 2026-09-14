"""Search Qiskit's stochastic layout/routing choices on the exact 190 QASM."""
import hashlib, json
from pathlib import Path
from qiskit import qasm2, transpile
from qiskit.quantum_info import Operator
from distributed_frame_search import materialize_output_layout

def equiv(a,b):
    x,y=Operator(a).data,Operator(b).data
    i,j=divmod(abs(x).argmax(),x.shape[1]); p=x[i,j]/y[i,j]
    return bool(max(abs(x-p*y).flat)<1e-8)

def run(out, seeds=64):
    assert not out.exists();out.mkdir(parents=True)
    source=Path('artifacts/190/two_stage_190.qasm'); base=qasm2.load(source)
    best=(base.depth(),base.count_ops().get('cx',0)); rows=[]
    for seed in range(seeds):
        q=materialize_output_layout(transpile(base,basis_gates=['u3','cx'],
            qubits_initially_zero=False,optimization_level=3,seed_transpiler=seed))
        row=dict(seed=seed,depth=q.depth(),cx=q.count_ops().get('cx',0),equiv=equiv(q,base))
        rows.append(row)
        if row['equiv'] and (row['depth'],row['cx'])<best:
            best=(row['depth'],row['cx']); p=out/f'oracle_d{best[0]}_cx{best[1]}.qasm';p.write_text(qasm2.dumps(q));row['path']=str(p)
            print('IMPROVEMENT',row,flush=True)
        if seed%8==0: print('seed',seed,'best',best,flush=True)
    (out/'report.json').write_text(json.dumps(dict(source=str(source.resolve()),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),best=best,rows=rows),indent=2)+'\n')
    print('done',best,flush=True)
if __name__=='__main__': run(Path('artifacts/post190_transpiler_seed_v2'), seeds=8)
