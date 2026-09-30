"""Build a bounded independent-pass codebook candidate; never promote unverified."""
import json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
import level_oracle as l
from distributed_ucry import structured_ucry,verify_component
from distributed_frame_search import native


def run(outdir):
    assert not outdir.exists();outdir.mkdir(parents=True)
    rows=json.loads(Path('artifacts/post258_codebook_screen.json').read_text())
    records={r['side']:r['independent_pass_best'] for r in rows}
    components={}; checks=[]
    for side,record in records.items():
        a,b=[np.array(l.angle_table(l.code_of(record[label],l.LEVEL[side+str(p)])[1]))
             for p,label in [(1,'first'),(2,'second')]]
        for stage,tables in enumerate([a,b-a,-b]):
            short=[]
            for seed in range(24):
                for sparse,opened in [(False,True),(True,False)]:
                    raw=structured_ucry(tables,[6,7,8],list(range(6)),seed,sparse=sparse,open_walk=opened)
                    short.append((raw.depth(),raw.size(),seed,sparse,opened,raw))
            short.sort(key=lambda r:r[:2]);candidates=[]
            for _,_,seed,sparse,opened,raw in short[:4]:
                c=native(raw);candidates.append((c.depth(),c.size(),seed,sparse,opened,c))
            depth,_,seed,sparse,opened,c=min(candidates,key=lambda r:r[:2])
            err=verify_component(c,tables)
            components[side,stage]=c
            checks.append(dict(side=side,stage=stage,depth=depth,cx=c.count_ops().get('cx',0),seed=seed,sparse=sparse,open_walk=opened,error=err))
    q=QuantumCircuit(18); kernels=[]
    for stage in range(3):
        q.compose(components['u',stage],l.YW+l.YA,inplace=True)
        q.compose(components['v',stage],l.XW+l.XA,inplace=True)
        if stage<2:
            key=['first','second'][stage]
            ac=l.code_of(records['u'][key],l.LEVEL['u1'])[0]
            bc=l.code_of(records['v'][key],l.LEVEL['v1'])[0]
            terms=l.kernel_terms(ac,bc)
            k=QuantumCircuit(6);l.emit_kernel(k,terms,[0,1,2],[3,4,5]);k=native(k)
            q.compose(k,l.YA+l.XA,inplace=True)
            kernels.append(dict(depth=k.depth(),cx=k.count_ops().get('cx',0),terms=terms))
    q=native(q);path=outdir/f'independent_codes_d{q.depth()}.qasm';path.write_text(qasm2.dumps(q))
    record=dict(depth=q.depth(),cx=q.count_ops().get('cx',0),records=records,components=checks,kernels=kernels,qasm=str(path))
    (outdir/'report.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2),flush=True)
    from exhaustive_verify import exhaustive
    exhaustive(path)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);run(p.parse_args().outdir)
