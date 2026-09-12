"""Optimize integer phase lifts using phases supported only on unreachable codes."""
import argparse,json,math,random
from pathlib import Path
import numpy as np
from depth_parity_network import walsh
from post258_two_stage_anf import decode
import two_stage_oracle as ts


def run(record,outdir,steps,seed):
    assert not outdir.exists();outdir.mkdir(parents=True)
    r=json.loads(record.read_text());yl,xl=decode(r['ylab']),decode(r['xlab'])
    yr={k[0]|(v<<1) for k,v in yl.items()};xr={k[0]|(v<<1) for k,v in xl.items()}
    care=np.array([y|(x<<4) for y in yr for x in xr])
    lift=np.array([sum(m&~w==0 for m in r['terms']) for w in range(256)],float)
    a=np.rint(-32*walsh(lift)).astype(int);assert np.max(abs(a+32*walsh(lift)))<1e-9
    a=(a+16)%32-16;a[0]=0
    moves=[]
    for side,missing in [(0,set(range(16))-yr),(1,set(range(16))-xr)]:
        for value in missing:
            for mask in range(16):
                for mode in ['character','parity']:
                    null=[]
                    for w in range(256):
                        this=(w>>(4*side))&15;other=(w>>(4*(1-side)))&15
                        b=(mask&other).bit_count()&1
                        null.append(int(this==value)*((-1)**b if mode=='character' else b))
                    assert not np.any(np.array(null)[care])
                    delta=-32*walsh(null);assert np.max(abs(delta-np.rint(delta)))<1e-9
                    delta=np.rint(delta).astype(int);delta[0]=0
                    if np.any(delta):moves.append(delta)
    moves=np.unique(np.array(moves),axis=0)
    candidates=np.unique(np.concatenate([moves*k for k in [1,-1,2,-2,4,-4,8,-8,16]]),axis=0)
    rng=random.Random(seed);best=int(np.count_nonzero(a));cur=a.copy();history=[]
    # Phase ratios must be common across every reachable point after changes.
    P=np.array([[(w&m).bit_count()&1 for m in range(256)] for w in care],int)
    want=np.exp(1j*math.pi*lift[care])
    for step in range(steps):
        allnext=(cur[None,:]+candidates+16)%32-16
        counts=np.count_nonzero(allnext,axis=1)
        m=int(counts.min());ids=np.flatnonzero(counts==m)
        idx=int(rng.choice(ids));nxt=allnext[idx]
        current=int(np.count_nonzero(cur))
        if m<current or (m==current and rng.random()<0.3):cur=nxt
        else:
            idx=rng.randrange(len(candidates));nxt=allnext[idx]
            temp=0.2+1.5*(1-(step%100)/100)
            if rng.random()<math.exp(min(0,(current-int(counts[idx]))/temp)):cur=nxt
        score=int(np.count_nonzero(cur))
        if score<best or step==0:
            best=score
            actual=np.exp(1j*math.pi/16*(P@cur));rat=actual/want;err=float(np.max(abs(rat-rat[0])));assert err<1e-10
            row=dict(step=step,terms=score,coefficients=cur.tolist(),error=err,record=str(record));history.append(row)
            (outdir/f'phase_step{step}_terms{score}.json').write_text(json.dumps(row,indent=2)+'\n');print('phase terms',step,score,'error',err,flush=True)
    (outdir/'report.json').write_text(json.dumps(dict(steps=steps,seed=seed,moves=len(candidates),improvements=history),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--record',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--steps',type=int,default=300);p.add_argument('--seed',type=int,default=0);a=p.parse_args();run(a.record,a.outdir,a.steps,a.seed)
