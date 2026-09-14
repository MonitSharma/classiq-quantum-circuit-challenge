"""Search class-only 4-bit descriptor assignments for low ANF complexity.

Unlike the current raw-conditioned 3-bit codes, this asks whether four bits
constant on each side's equivalence class can be cheaper to synthesize.  It is
an exact semantic screen: labels are injective across the eleven classes and
their ANF statistics are computed over all 64 coordinates.  The result is a
descriptor hypothesis, not a circuit candidate.
"""
import argparse, json, math, random, time
from pathlib import Path
import two_stage_oracle as ts


def anf(vals):
    a=list(vals)
    for b in range(6):
        for m in range(64):
            if m>>b&1: a[m]^=a[m^(1<<b)]
    return a


def stats(labels, classes):
    vals=[labels[c] for c in classes]
    coeff=[anf([(v>>b)&1 for v in vals]) for b in range(4)]
    terms=sum(sum(row) for row in coeff)
    weighted=sum((1+m.bit_count())*row[m] for row in coeff for m in range(64))
    degree=max((m.bit_count() for row in coeff for m in range(64) if row[m]),default=0)
    return (terms,weighted,degree), [[m for m in range(64) if row[m]] for row in coeff]


def run(outdir, side, seconds, seeds, seed):
    outdir.mkdir(parents=True,exist_ok=True); classes=ts.ROWCLS if side=='y' else ts.COLCLS
    n=max(classes)+1; rng=random.Random(seed); start=time.monotonic(); best=None; rows=[]
    for restart in range(seeds):
        labels=list(range(n)); rng.shuffle(labels)
        cur,_=stats(labels,classes); temp=3.0
        for step in range(200000):
            if time.monotonic()-start>=seconds: break
            a,b=rng.sample(range(n),2); labels[a],labels[b]=labels[b],labels[a]
            nxt,terms=stats(labels,classes)
            accept=nxt<=cur or rng.random()<math.exp((cur[0]-nxt[0])/max(.05,temp))
            if accept: cur=nxt
            else: labels[a],labels[b]=labels[b],labels[a]
            temp*=.99995
            if best is None or cur<best[0]:
                _,terms=stats(labels,classes);best=(cur,labels[:],terms)
                row={'side':side,'restart':restart,'step':step,'stats':cur,'labels':labels[:],'anf_terms':terms}
                rows.append(row); print(row,flush=True)
                (outdir/'best.json').write_text(json.dumps(row,indent=2)+'\n')
        if time.monotonic()-start>=seconds: break
    result={'side':side,'seconds':time.monotonic()-start,'best':rows[-1] if rows else None,'improvements':rows}
    (outdir/'search.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--seconds',type=float,default=60);p.add_argument('--seeds',type=int,default=8);p.add_argument('--seed',type=int,default=0);a=p.parse_args();run(a.outdir,a.side,a.seconds,a.seeds,a.seed)
