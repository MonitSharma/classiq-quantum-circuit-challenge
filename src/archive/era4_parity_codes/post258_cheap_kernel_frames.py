"""Joint two-pass linear-code frames, preserving the verified 13-layer kernel."""
import argparse,itertools,json
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
import level_oracle as l
from distributed_frame_search import FRAMES,transformed,frame_circuit,native
from distributed_ucry import structured_ucry,walsh
from level_encoder_search_fast import CODES


def candidates(side,keep,all_same=False):
    original=CODES[0][side=='v']
    tables={};spec={}
    for f in FRAMES:
        triple=transformed(original,f)
        tables[f]=[np.array(l.angle_table(l.code_of(triple,l.LEVEL[side+str(p)])[1])) for p in (1,2)]
        spec[f]=[np.rint(walsh(v)*64/np.pi).astype(int) for v in tables[f]]
    ranked=[]
    for f in FRAMES:
        if f!=tuple(sorted(f)):continue
        for g in FRAMES:
            coeff=[spec[f][0],spec[g][1]-spec[f][0],spec[g][1]]
            counts=[np.count_nonzero(v,axis=1).tolist() for v in coeff]
            framecx=len(FRAMES[f])+len(FRAMES[g])
            # Expose both host bottleneck and term count, including frame overhead.
            proxy=sum(max(v) for v in counts)+2*framecx
            ranked.append((proxy,sum(map(sum,counts)),framecx,f,g,counts))
    ranked.sort()
    selected=([r for r in ranked if r[3]==r[4]] if all_same else ranked[:keep])
    # Include the spectral optimum as a distinct comparison.
    selected.append(min(ranked,key=lambda r:r[1]))
    selected.append(next(r for r in ranked if r[3]==r[4]==(1,2,4)))
    found=[]
    for _,terms,_,f,g in dict.fromkeys((r[:5] for r in selected)):
        a=tables[f][0];b=tables[g][1];comps=[];settings=[]
        for angles in [a,b-a,-b]:
            options=[]
            for seed in range(24):
                for sparse,opened in [(False,True),(True,False)]:
                    q=structured_ucry(angles,[6,7,8],list(range(6)),seed,sparse=sparse,open_walk=opened)
                    options.append((q.depth(),q.size(),seed,sparse,opened,q))
            options.sort(key=lambda r:r[:2]);chosen=[]
            for _,_,seed,sparse,opened,q in options[:3]:
                q=native(q);chosen.append((q.depth(),q.size(),seed,sparse,opened,q))
            best=min(chosen,key=lambda r:r[:2]);comps.append(best[-1]);settings.append(best[:5])
        rec=dict(first=f,second=g,terms=terms,settings=settings,depths=[q.depth() for q in comps])
        print(side,rec,flush=True);found.append((rec,comps))
    return found


def run(outdir,keep,all_same=False):
    assert not outdir.exists();outdir.mkdir(parents=True)
    ys=candidates('u',keep,all_same);xs=candidates('v',keep,all_same)
    base=qasm2.load('artifacts/258/kernel.qasm');best=(9999,9999);records=[]
    for (yr,yq),(xr,xq) in itertools.product(ys,xs):
        q=QuantumCircuit(18);kd=[]
        for stage in range(3):
            q.compose(yq[stage],l.YW+l.YA,inplace=True);q.compose(xq[stage],l.XW+l.XA,inplace=True)
            if stage<2:
                key=['first','second'][stage]
                k=QuantumCircuit(6)
                yf=frame_circuit(yr[key]);xf=frame_circuit(xr[key])
                k.compose(yf.inverse(),[0,1,2],inplace=True);k.compose(xf.inverse(),[3,4,5],inplace=True)
                k.compose(base,inplace=True)
                k.compose(yf,[0,1,2],inplace=True);k.compose(xf,[3,4,5],inplace=True)
                k=native(k);kd.append(k.depth());q.compose(k,l.YA+l.XA,inplace=True)
        q=native(q);score=(q.depth(),q.count_ops().get('cx',0))
        rec=dict(y=yr,x=xr,depth=score[0],cx=score[1],kernel_depths=kd);records.append(rec)
        if score<best:
            best=score;path=outdir/f'candidate{len(records)}_d{score[0]}.qasm';path.write_text(qasm2.dumps(q));rec['path']=str(path)
            print('best',score,str(path),flush=True)
    (outdir/'report.json').write_text(json.dumps(records,indent=2)+'\n')
    win=min(records,key=lambda r:(r['depth'],r['cx']))
    from exhaustive_verify import exhaustive
    exhaustive(Path(win['path']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--keep',type=int,default=6);p.add_argument('--all-same',action='store_true');a=p.parse_args();run(a.outdir,a.keep,a.all_same)
