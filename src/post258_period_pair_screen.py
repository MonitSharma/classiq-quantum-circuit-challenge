"""Complete period-pair screen, then feasible triples, using proven singleton pruning."""
import itertools,json,time
from pathlib import Path
import z3
import two_stage_oracle as t


def run(outdir):
    assert not outdir.exists();outdir.mkdir(parents=True)
    singleton=json.loads(Path('artifacts/post258_single_period.json').read_text())
    for rec in singleton:
        side,raw=rec['side'],rec['raw'];cls=t.ROWCLS if side=='y' else t.COLCLS
        pool=[r['direction'] for r in rec['results'] if r['status']!='unsat']
        c=[z3.BitVec(f'{side}_c{i}',3) for i in range(64)];s=z3.Solver();s.set(timeout=2000)
        for a in range(64):
            for b in range(a):
                if ((a^b)>>raw&1)==0 and cls[a]!=cls[b]:s.add(c[a]!=c[b])
        s.add(c[0]==0)
        cond={(b,d):[z3.Extract(b,b,c[a])==z3.Extract(b,b,c[a^d]) for a in range(64) if a<(a^d)] for b in range(3) for d in pool}
        def check(ds):
            s.push()
            for b,d in enumerate(ds):s.add(cond[b,d])
            before=time.monotonic();st=s.check();r=dict(directions=ds,status=str(st),seconds=time.monotonic()-before)
            if st==z3.sat:r['labels']=[s.model().eval(v).as_long() for v in c]
            s.pop();return r
        pairs=[];allowed=set()
        for ds in itertools.combinations_with_replacement(pool,2):
            r=check(ds);pairs.append(r)
            if r['status']!='unsat':allowed.add(ds)
        print(side,'pairs',len(pairs),'not UNSAT',len(allowed),flush=True)
        (outdir/f'{side}_pairs.json').write_text(json.dumps(pairs,indent=2)+'\n')
        triples=[]
        for ds in itertools.combinations_with_replacement(pool,3):
            if not all(pair in allowed for pair in itertools.combinations(ds,2)):continue
            r=check(ds);triples.append(r)
            if r['status']=='sat':print(side,'SAT triple',ds,flush=True)
        (outdir/f'{side}_triples.json').write_text(json.dumps(triples,indent=2)+'\n')
        print(side,'triples',len(triples),{st:sum(r['status']==st for r in triples) for st in ['sat','unsat','unknown']},flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);run(p.parse_args().outdir)
