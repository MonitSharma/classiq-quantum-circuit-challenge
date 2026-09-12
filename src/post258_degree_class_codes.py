"""SAT degree screen for split class encodings, preserving raw coordinate bit."""
import argparse,json,time
from pathlib import Path
import z3
import two_stage_oracle as t


def run(outdir,timeout,profiles=False):
    assert not outdir.exists();outdir.mkdir(parents=True)
    rows=[]
    for side,cls,raw in [('y',t.ROWCLS,5),('x',t.COLCLS,4)]:
        for degree in ([(2,4,4),(3,3,4),(2,5,5),(1,6,6)] if profiles else [3,4,5]):
            code=[z3.BitVec(f'{side}_{degree}_{i}',3) for i in range(64)]
            s=z3.Solver();s.set(timeout=timeout)
            for a in range(64):
                for b in range(a):
                    if ((a^b)>>raw&1)==0 and cls[a]!=cls[b]:s.add(code[a]!=code[b])
            s.add(code[0]==0)
            for mask in range(64):
                if not isinstance(degree,tuple) and mask.bit_count()<=degree:continue
                value=z3.BitVecVal(0,3)
                for x in range(64):
                    if x&~mask==0:value=value^code[x]
                if isinstance(degree,tuple):
                    for bit,d in enumerate(degree):
                        if mask.bit_count()>d:s.add(z3.Extract(bit,bit,value)==0)
                else:s.add(value==0)
            start=time.monotonic();status=s.check();row=dict(side=side,raw=raw,degree=degree,status=str(status),seconds=time.monotonic()-start)
            if status==z3.sat:
                labels=[s.model().eval(c).as_long() for c in code];anf=labels.copy()
                for bit in range(6):
                    for mask in range(64):
                        if mask>>bit&1:anf[mask]^=anf[mask^(1<<bit)]
                if isinstance(degree,tuple):
                    assert all(not (anf[m]>>bit&1) for bit,d in enumerate(degree) for m in range(64) if m.bit_count()>d)
                else:assert all(not anf[m] for m in range(64) if m.bit_count()>degree)
                row.update(labels=labels,anf=anf)
            rows.append(row);print({k:v for k,v in row.items() if k not in ['labels','anf']},flush=True)
            (outdir/'report.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--timeout-ms',type=int,default=10000);p.add_argument('--profiles',action='store_true');a=p.parse_args();run(a.outdir,a.timeout_ms,a.profiles)
