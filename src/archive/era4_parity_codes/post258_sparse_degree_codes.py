"""Bounded Boolean optimization of degree-four split class encoders."""
import argparse,json,time
from pathlib import Path
import z3
import two_stage_oracle as t


def run(outdir,timeout):
    assert not outdir.exists();outdir.mkdir(parents=True)
    rows=[]
    for side,cls,raw in [('y',t.ROWCLS,5),('x',t.COLCLS,4)]:
        code=[z3.BitVec(f'{side}_{i}',3) for i in range(64)]
        s=z3.Optimize();s.set(timeout=timeout)
        for a in range(64):
            for b in range(a):
                if ((a^b)>>raw&1)==0 and cls[a]!=cls[b]:s.add(code[a]!=code[b])
        s.add(code[0]==0)
        anf=[]
        for mask in range(64):
            val=z3.BitVecVal(0,3)
            for x in range(64):
                if x&~mask==0:val=val^code[x]
            anf.append(val)
            if mask.bit_count()>4:s.add(val==0)
        degree4=z3.Sum([z3.If(z3.Extract(b,b,anf[m])==1,1,0) for m in range(64) if m.bit_count()==4 for b in range(3)])
        degree3=z3.Sum([z3.If(z3.Extract(b,b,anf[m])==1,1,0) for m in range(64) if m.bit_count()==3 for b in range(3)])
        degree2=z3.Sum([z3.If(z3.Extract(b,b,anf[m])==1,1,0) for m in range(64) if m.bit_count()==2 for b in range(3)])
        obj=s.minimize(4*degree4+2*degree3+degree2)
        start=time.monotonic();st=s.check();row=dict(side=side,raw=raw,status=str(st),seconds=time.monotonic()-start)
        try:
            model=s.model();labels=[model.eval(c).as_long() for c in code]
            # Independently validate any incumbent returned on timeout.
            assert all(cls[a]==cls[b] or ((a^b)>>raw&1) or labels[a]!=labels[b] for a in range(64) for b in range(a))
            aa=labels.copy()
            for bit in range(6):
                for m in range(64):
                    if m>>bit&1:aa[m]^=aa[m^(1<<bit)]
            assert all(not aa[m] for m in range(64) if m.bit_count()>4)
            row.update(labels=labels,anf=aa,counts={str(d):sum(aa[m].bit_count() for m in range(64) if m.bit_count()==d) for d in range(5)},lower=str(obj.lower()),upper=str(obj.upper()))
        except (z3.Z3Exception,AttributeError,AssertionError):row['incumbent_validated']=False
        rows.append(row);print({k:v for k,v in row.items() if k not in ['labels','anf']},flush=True)
        (outdir/'report.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--timeout-ms',type=int,default=20000);a=p.parse_args();run(a.outdir,a.timeout_ms)
