"""Exact SAT screen for short-period class encoders in the two-stage layout.

Only raw-bit plus loaded code must distinguish different row/column classes.
Inputs of the same class may use different codes. Each loaded bit is invariant
under its own coordinate XOR direction. SAT/UNSAT/UNKNOWN remain distinct.
"""
import argparse,itertools,json,time
from pathlib import Path
import z3
import two_stage_oracle as t


def screen(side,directions,timeout_ms,outdir):
    cls,raw=(t.ROWCLS,5) if side=='y' else (t.COLCLS,4)
    code=[z3.BitVec(f'{side}_{i}',3) for i in range(64)]
    s=z3.Solver();s.set(timeout=timeout_ms)
    for a in range(64):
        for b in range(a):
            if ((a^b)>>raw&1)==0 and cls[a]!=cls[b]:s.add(code[a]!=code[b])
    s.add(code[0]==0)
    periods={(bit,d):[z3.Extract(bit,bit,code[a])==z3.Extract(bit,bit,code[a^d])
                        for a in range(64) if a<(a^d)] for bit in range(3) for d in directions}
    results=[];start=time.monotonic()
    # Repeated directions also covered: bit permutations are a symmetry here.
    for ds in itertools.combinations_with_replacement(directions,3):
        s.push()
        for bit,d in enumerate(ds):s.add(periods[bit,d])
        before=time.monotonic();status=s.check()
        row=dict(directions=ds,status=str(status),seconds=time.monotonic()-before)
        if status==z3.sat:
            model=s.model();labels=[model.eval(c).as_long() for c in code]
            for a in range(64):
                for b in range(a):
                    assert cls[a]==cls[b] or (a>>raw&1)!=(b>>raw&1) or labels[a]!=labels[b]
            for bit,d in enumerate(ds):assert all(((labels[a]^labels[a^d])>>bit&1)==0 for a in range(64))
            row['labels']=labels
            print('SAT',side,row,flush=True)
        s.pop();results.append(row)
        if status==z3.sat:break
        if len(results)%20==0: print(side,len(results),{x:sum(r['status']==x for r in results) for x in ['sat','unsat','unknown']},flush=True)
    report=dict(side=side,raw=raw,direction_pool=directions,timeout_ms=timeout_ms,elapsed=time.monotonic()-start,results=results)
    (outdir/f'{side}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(side,'done',len(results),report['elapsed'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--max-weight',type=int,default=1);p.add_argument('--timeout-ms',type=int,default=1000)
    a=p.parse_args();assert not a.outdir.exists();a.outdir.mkdir(parents=True)
    ds=[d for d in range(1,64) if d.bit_count()<=a.max_weight]
    for side in ['y','x']:screen(side,ds,a.timeout_ms,a.outdir)
