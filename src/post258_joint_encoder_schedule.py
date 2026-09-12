"""Optimize complete E K E^-1 depth rather than isolated encoder depth."""
import argparse,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from distributed_ucry import structured_ucry
from distributed_frame_search import native
from post258_two_stage_anf import decode
import two_stage_oracle as ts


def touches(q,initial=None):
    d=[0]*q.num_qubits if initial is None else initial.copy()
    for inst in q.data:
        wires=[q.find_bit(b).index for b in inst.qubits];v=max(d[b] for b in wires)+1
        for b in wires:d[b]=v
    return d


def run(record,kernel,outdir,seeds):
    assert not outdir.exists();outdir.mkdir(parents=True)
    r=json.loads(record.read_text());bags=[]
    for side,cls,mask,lab in [(0,ts.ROWCLS,32,decode(r['ylab'])),(1,ts.COLCLS,r['xmask'],decode(r['xlab']))]:
        codes=[lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)]
        table=np.array([[math.pi*(c>>b&1) for c in codes] for b in range(3)])
        raw=(mask&-mask).bit_length()-1;bag={}
        for seed in range(seeds):
            for sparse,opened in [(False,True),(True,False)]:
                e=native(structured_ucry(table,[6,7,8],list(range(6)),seed,sparse=sparse,open_walk=opened))
                for b in range(6):
                    if b!=raw and mask>>b&1:e.cx(b,raw)
                times=touches(e);key=tuple(times)
                if key not in bag or e.size()<bag[key][0].size():bag[key]=(e,dict(seed=seed,sparse=sparse,opened=opened,times=times,raw=raw))
        vals=list(bag.values());pareto=[]
        for e,row in vals:
            if not any(all(a<=b for a,b in zip(other['times'],row['times'])) and other['times']!=row['times'] for _,other in vals):pareto.append((e,row))
        bags.append(pareto);print('side',side,'distinct',len(vals),'pareto',len(pareto),flush=True)
    k=qasm2.load(kernel);pairs=[]
    for ey,ry in bags[0]:
        for ex,rx in bags[1]:
            before=rx['times'][:6]+ry['times'][:6]+ry['times'][6:]+rx['times'][6:]
            kw=[ry['raw']+6,12,13,14,rx['raw'],15,16,17]
            after=before.copy();sub=touches(k,[before[w] for w in kw])
            for w,t in zip(kw,sub):after[w]=t
            depth=max(a+b for a,b in zip(after,before))
            pairs.append((depth,ey.size()+ex.size(),ey,ex,ry,rx,kw))
    best=(9999,9999);records=[]
    for predicted,_,ey,ex,ry,rx,kw in sorted(pairs,key=lambda t:t[:2])[:12]:
        enc=QuantumCircuit(18);enc.compose(ey,ts.YW+ts.YA,inplace=True);enc.compose(ex,ts.XW+ts.XA,inplace=True)
        raw=enc.compose(k,kw).compose(enc.inverse());assert raw.depth()==predicted,(raw.depth(),predicted)
        q=native(raw);score=(q.depth(),q.count_ops().get('cx',0))
        row=dict(predicted=predicted,depth=score[0],cx=score[1],y=ry,x=rx);records.append(row)
        if score<best:
            best=score;path=outdir/f'joint_d{score[0]}_cx{score[1]}.qasm';path.write_text(qasm2.dumps(q));row['path']=str(path)
            print('best',row,flush=True)
            from exhaustive_verify import exhaustive
            exhaustive(path)
    (outdir/'report.json').write_text(json.dumps(dict(record=str(record),kernel=str(kernel),seeds=seeds,rows=records),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record',type=Path,required=True);p.add_argument('--kernel',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=120);a=p.parse_args();run(a.record,a.kernel,a.outdir,a.seeds)
