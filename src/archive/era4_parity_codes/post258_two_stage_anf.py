"""Joint raw-conditioned class labels and low-degree kernel phase lifts.

The kernel is solved on reachable pairs only. An ANF polynomial is lifted by
ordinary integer addition before Walsh synthesis; this preserves exp(i*pi*f)
and can have much sparser spectrum than the Boolean representative.
"""
import argparse,json,math,random,time
from pathlib import Path
import numpy as np
import two_stage_oracle as ts

ORDER=sorted(range(256),key=lambda m:(m.bit_count(),m))
EVAL=[]
for w in range(256):
    EVAL.append(sum(1<<i for i,m in enumerate(ORDER) if m&~w==0))
COST=[0.05 if m.bit_count()<2 else [0,0,0.5,1,4,12,30,80,200][m.bit_count()] for m in ORDER]
YK=list(ts.YCELL);XK=list(ts.XCELL)
WANT={(y,x):int(ts.logo(ts.XCELL[x][0],ts.YCELL[y][0])) for y in YK for x in XK}


def polynomial(yl,xl):
    piv={}
    for y in YK:
        for x in XK:
            w=y[0]|(yl[y]<<1)|(x[0]<<4)|(xl[x]<<5)
            row=EVAL[w];rhs=WANT[y,x]
            while row:
                i=(row&-row).bit_length()-1
                if i in piv:
                    a,b=piv[i];row^=a;rhs^=b
                else:piv[i]=(row,rhs);break
            assert row or rhs==0
    sol=0
    for i in sorted(piv,reverse=True):
        row,rhs=piv[i]
        if ((row&sol).bit_count()&1)^rhs:sol|=1<<i
    return sol


def cost(sol):return sum(COST[i] for i in range(256) if sol>>i&1)
def encode(lab):return {','.join(map(str,k)):v for k,v in lab.items()}
def decode(lab):return {tuple(map(int,k.split(','))):v for k,v in lab.items()}


def search(outdir,steps,seed):
    assert not outdir.exists();outdir.mkdir(parents=True)
    rng=random.Random(seed)
    yl={};xl={}
    for lab,keys in [(yl,YK),(xl,XK)]:
        for b in [0,1]:
            ks=[k for k in keys if k[0]==b]
            for v,k in enumerate(ks):lab[k]=v
    sol=polynomial(yl,xl);cur=cost(sol);best=cur;records=[];start=time.monotonic()
    for step in range(steps):
        sy=rng.randrange(2);lab=yl if sy else xl;keys=YK if sy else XK
        a=rng.choice(keys);value=rng.randrange(8)
        other=next((k for k in keys if k[0]==a[0] and lab[k]==value),None)
        prev=lab[a];lab[a]=value
        if other is not None:lab[other]=prev
        newsol=polynomial(yl,xl);val=cost(newsol)
        temp=0.5+3*(1-(step%1000)/1000)
        accept=val<=cur or rng.random()<math.exp(min(0,(cur-val)/temp))
        if accept:cur,sol=val,newsol
        else:
            lab[a]=prev
            if other is not None:lab[other]=value
        if cur<best or step==0:
            best=cur;terms=[ORDER[i] for i in range(256) if sol>>i&1]
            lifted=[sum(int(m&~w==0) for m in terms) for w in range(256)]
            spectrum=ts.walsh8(lifted)
            row=dict(step=step,cost=cur,terms=terms,degree_histogram={str(k):sum(m.bit_count()==k for m in terms) for k in range(9)},parity_terms=int(np.count_nonzero(abs(spectrum[1:])>1e-12)),ylab=encode(yl),xlab=encode(xl))
            records.append(row);print({k:v for k,v in row.items() if k not in ['ylab','xlab','terms']},flush=True)
            (outdir/f'best_step{step}.json').write_text(json.dumps(row,indent=2)+'\n')
    (outdir/'search.json').write_text(json.dumps(dict(seed=seed,steps=steps,seconds=time.monotonic()-start,improvements=records),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--steps',type=int,default=4000);p.add_argument('--seed',type=int,default=0);a=p.parse_args();search(a.outdir,a.steps,a.seed)
