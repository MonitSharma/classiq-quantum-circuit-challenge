"""Allow within-cell split codes for the enumerated nonlinear tags."""
import argparse,json,time
from pathlib import Path
import z3
import two_stage_oracle as ts


def run(source,outdir,degree,timeout,limit):
    assert not outdir.exists();outdir.mkdir(parents=True);data=json.loads(source.read_text());side=data['side'];cls=ts.ROWCLS if side=='y' else ts.COLCLS
    candidates=sorted(data['viable'],key=lambda r:(sum(r['counts']),r['a'].bit_count()+r['b'].bit_count()+r['linear'].bit_count()))[:limit]
    rows=[]
    for idx,tag in enumerate(candidates):
        code=[z3.BitVec(f'c_{i}',3) for i in range(64)];s=z3.Solver();s.set(timeout=timeout);t=int(tag['tag'])
        for m in range(64):
            if m.bit_count()<=degree:continue
            v=z3.BitVecVal(0,3)
            for i in range(64):
                if i&~m==0:v=v^code[i]
            s.add(v==0)
        s.add(code[0]==0)
        for i in range(64):
            for j in range(i):
                if cls[i]!=cls[j] and (t>>i^t>>j)&1==0:s.add(code[i]!=code[j])
        start=time.monotonic();st=s.check();row=dict(index=idx,tag=tag,status=str(st),degree=degree,seconds=time.monotonic()-start)
        if st==z3.sat:
            labels=[s.model().eval(c).as_long() for c in code];anf=labels.copy()
            for b in range(6):
                for m in range(64):
                    if m>>b&1:anf[m]^=anf[m^(1<<b)]
            assert all(not anf[m] for m in range(64) if m.bit_count()>degree)
            assert all(cls[i]==cls[j] or (t>>i^t>>j)&1 or labels[i]!=labels[j] for i in range(64) for j in range(i))
            row.update(labels=labels,anf=anf)
        rows.append(row);print(side,idx,str(st),round(row['seconds'],2),flush=True)
        (outdir/'report.json').write_text(json.dumps(dict(side=side,degree=degree,rows=rows),indent=2)+'\n')
        if st==z3.sat:break


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--degree',type=int,default=3);p.add_argument('--timeout-ms',type=int,default=1500);p.add_argument('--limit',type=int,default=20);a=p.parse_args();run(a.source,a.outdir,a.degree,a.timeout_ms,a.limit)
