"""Low-degree four-bit class codes with a reversibly mutable coordinate output."""
import argparse,json,time
from pathlib import Path
import z3
import two_stage_oracle as t


def run(outdir,timeout):
    assert not outdir.exists();outdir.mkdir(parents=True);rows=[]
    for side,cls in [('y',t.ROWCLS),('x',t.COLCLS)]:
        for degree,raw in [(2,None),(3,None),(3,5)]:
            c=[z3.BitVec(f'{side}_{degree}_{raw}_{i}',4) for i in range(64)]
            s=z3.Solver();s.set(timeout=timeout)
            for a in range(64):
                for b in range(a):
                    if cls[a]!=cls[b]:s.add(c[a]!=c[b])
            s.add(c[0]==0)
            anf=[]
            for mask in range(64):
                value=z3.BitVecVal(0,4)
                for x in range(64):
                    if x&~mask==0:value=value^c[x]
                anf.append(value)
                if mask.bit_count()>degree:s.add(value==0)
                if raw is not None and mask>>raw&1:s.add(z3.Extract(0,0,value)==int(mask==(1<<raw)))
            start=time.monotonic();st=s.check();r=dict(side=side,degree=degree,raw=raw,status=str(st),seconds=time.monotonic()-start)
            if st==z3.sat:
                labels=[s.model().eval(v).as_long() for v in c];coeff=[s.model().eval(v).as_long() for v in anf]
                assert all(cls[a]==cls[b] or labels[a]!=labels[b] for a in range(64) for b in range(a))
                r.update(labels=labels,anf=coeff)
            rows.append(r);print({k:v for k,v in r.items() if k not in ['labels','anf']},flush=True)
            (outdir/'report.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--timeout-ms',type=int,default=15000);a=p.parse_args();run(a.outdir,a.timeout_ms)
