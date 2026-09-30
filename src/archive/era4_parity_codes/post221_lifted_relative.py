"""Current class codes with integer angle lifts and phase-tolerant boundaries."""
import argparse,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from post258_encoder_lifts import best_lift
from post224_relative_lookup import relative
from distributed_ucry import structured_ucry
from distributed_frame_search import native
from post258_two_stage_anf import decode
from post258_joint_encoder_schedule import touches
import two_stage_oracle as ts


def sparse_relative(table,seed):
    q=structured_ucry(table,[6,7,8],list(range(6)),seed,sparse=True)
    body=list(q.data)[3:-3]
    while body and body[-1].operation.name=='cx':
        a,b=[q.find_bit(w).index for w in body[-1].qubits]
        if a>=6 or b<6:break
        body.pop()
    out=QuantumCircuit(9)
    for b in range(6,9):out.h(b)
    for inst in body:out.append(inst.operation,[q.find_bit(w).index for w in inst.qubits])
    for b in range(6,9):out.h(b)
    return native(out)


def run(outdir,seeds):
    assert not outdir.exists();outdir.mkdir(parents=True)
    r=json.loads(Path('artifacts/221/class_codes.json').read_text());bags=[];details=[]
    for side,cls,mask,key in [(0,ts.ROWCLS,32,'ylab'),(1,ts.COLCLS,48,'xlab')]:
        lab=decode(r[key]);codes=[lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)]
        original=np.array([[c>>b&1 for c in codes] for b in range(3)])
        lift=[best_lift(t,side*3+b) for b,t in enumerate(original)]
        angles=np.array([v[0] for v in lift])*math.pi
        row=dict(side=side,lifts=[v[1] for v in lift],angles=(angles/math.pi).round().astype(int).tolist());details.append(row)
        print('lift',row,flush=True)
        bag={}
        for kind,table in [('original',math.pi*original),('lift',angles)]:
            for seed in range(seeds):
                for sparse in [False,True]:
                    e=sparse_relative(table,seed) if sparse else relative(table,seed)[0]
                    if side:e.cx(5,4)
                    times=tuple(touches(e));meta=dict(kind=kind,seed=seed,sparse=sparse,depth=e.depth(),times=times)
                    if times not in bag or e.size()<bag[times][0].size():bag[times]=(e,meta)
        vals=list(bag.values());pareto=[(e,m) for e,m in vals if not any(all(a<=b for a,b in zip(o['times'],m['times'])) and o['times']!=m['times'] for _,o in vals)]
        bags.append(pareto);print('side',side,'best',min(m['depth'] for _,m in vals),'pareto',len(pareto),flush=True)
    k=qasm2.load('artifacts/221/kernel.qasm');kw=[11,12,13,14,4,15,16,17];pairs=[]
    for ey,my in bags[0]:
        for ex,mx in bags[1]:
            before=list(mx['times'][:6]+my['times'][:6]+my['times'][6:]+mx['times'][6:]);after=before.copy()
            for w,t in zip(kw,touches(k,[before[w] for w in kw])):after[w]=t
            pairs.append((max(a+b for a,b in zip(before,after)),ey,ex,my,mx))
    best=(9999,9999);rows=[]
    for prediction,ey,ex,my,mx in sorted(pairs,key=lambda v:v[0])[:60]:
        enc=QuantumCircuit(18);enc.compose(ey,ts.YW+ts.YA,inplace=True);enc.compose(ex,ts.XW+ts.XA,inplace=True)
        q=native(enc.compose(k,kw).compose(enc.inverse()));score=(q.depth(),q.count_ops().get('cx',0));row=dict(depth=score[0],cx=score[1],y=my,x=mx);rows.append(row)
        if score<best:
            best=score;path=outdir/f'lift_d{score[0]}_cx{score[1]}.qasm';path.write_text(qasm2.dumps(q));row['path']=str(path);print('best',row,flush=True)
            from exhaustive_verify import exhaustive
            exhaustive(path)
    (outdir/'report.json').write_text(json.dumps(dict(lifts=details,rows=rows),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=64);a=p.parse_args();run(a.outdir,a.seeds)
