"""Search arbitrary-input-safe Ry encoder lifts equivalent on the clean targets.

Each integer lift has the required parity at every coordinate. The forward
lookup can change coordinate-dependent signs; its actual inverse cancels them.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from distributed_frame_search import native
from distributed_ucry import structured_ucry,verify_component
from post258_kernel_schedule import synth
from post258_two_stage_anf import decode
import two_stage_oracle as ts

H=np.array([[(-1)**((a&b).bit_count()%2) for b in range(64)] for a in range(64)],int)


def best_lift(truth,seed):
    rng=np.random.default_rng(seed);best=(np.count_nonzero(H@truth),int(np.sum(abs(H@truth))))
    chosen=truth.copy();record={'polarity':None}
    for polarity in range(64):
        a=np.array([truth[w^polarity] for w in range(64)])
        for b in range(6):
            for m in range(64):
                if m>>b&1:a[m]^=a[m^(1<<b)]
        masks=np.flatnonzero(a)
        cubes=np.array([[int(m&~(w^polarity)==0) for w in range(64)] for m in masks])
        spectra=cubes@H
        for restart in range(4):
            signs=np.ones(len(masks),int) if restart==0 else rng.choice([-1,1],len(masks))
            sp=signs@spectra
            for sweep in range(5):
                change=False
                for i in rng.permutation(len(masks)):
                    new=sp-2*signs[i]*spectra[i]
                    if (np.count_nonzero(new),np.sum(abs(new))) < (np.count_nonzero(sp),np.sum(abs(sp))):
                        sp=new;signs[i]*=-1;change=True
                if not change:break
            score=(np.count_nonzero(sp),int(np.sum(abs(sp))))
            if score<best:
                chosen=signs@cubes;best=score;record=dict(polarity=polarity,masks=masks.tolist(),signs=signs.tolist())
    assert np.all(chosen%2==truth)
    return chosen,dict(nonzero=int(best[0]),l1=best[1],**record)


def run(outdir,seeds):
    assert not outdir.exists();outdir.mkdir(parents=True)
    r=json.loads(Path('artifacts/243/class_codes.json').read_text())
    _,_,yt,xt=ts.code_tables(decode(r['ylab']),decode(r['xlab']))
    es=[];rows=[]
    for side,table in enumerate([yt,xt]):
        original=np.rint(table/math.pi).astype(int)
        lifts=[best_lift(t,side*3+b) for b,t in enumerate(original)]
        lifted=np.array([a for a,r in lifts]);angles=math.pi*lifted
        print('lifts',side,[r for a,r in lifts],flush=True)
        options=[]
        for variant,tab in [('original',table),('lifted',angles)]:
            for seed in range(seeds):
                for sparse,opened in [(False,True),(True,False)]:
                    q=structured_ucry(tab,[6,7,8],list(range(6)),seed,sparse=sparse,open_walk=opened)
                    options.append((q.depth(),q.size(),variant,seed,sparse,opened,q,tab))
        compiled=[]
        for item in sorted(options,key=lambda t:t[:2])[:8]:
            q=native(item[-2]);compiled.append((q.depth(),q.size(),'structured',item[2:6],q,item[-1]))
        for variant,tab in [('original',table),('lifted',angles)]:
            phases=np.array([-0.5*sum(tab[b,w&63]*(-1)**(w>>(6+b)&1) for b in range(3)) for w in range(512)])
            for seed in range(seeds):
                q=QuantumCircuit(9)
                for b in range(6,9):q.rx(math.pi/2,b)
                q.compose(synth(phases,seed),inplace=True)
                for b in range(6,9):q.rx(-math.pi/2,b)
                q=native(q);compiled.append((q.depth(),q.size(),'generic',(variant,seed),q,tab))
        d,_,method,settings,e,tab=min(compiled,key=lambda t:t[:2])
        error=verify_component(e,tab);es.append(e)
        row=dict(side=side,depth=d,method=method,settings=settings,error=error,lifts=[r for a,r in lifts],angles=(tab/math.pi).round().astype(int).tolist(),choices=[t[:4] for t in compiled])
        rows.append(row);print('encoder',side,d,method,settings,flush=True)
        (outdir/f'encoder_{side}.qasm').write_text(qasm2.dumps(e))
    enc=QuantumCircuit(18);enc.compose(es[0],ts.YW+ts.YA,inplace=True);enc.compose(es[1],ts.XW+ts.XA,inplace=True)
    k=qasm2.load('artifacts/243/kernel.qasm')
    q=native(enc.compose(k,ts.KERNEL_WIRES).compose(enc.inverse()))
    path=outdir/f'encoder_lifts_d{q.depth()}.qasm';path.write_text(qasm2.dumps(q))
    report=dict(encoders=rows,depth=q.depth(),cx=q.count_ops().get('cx',0),path=str(path))
    (outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('full',q.depth(),q.count_ops(),flush=True)
    from exhaustive_verify import exhaustive
    exhaustive(path)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=12);a=p.parse_args();run(a.outdir,a.seeds)
