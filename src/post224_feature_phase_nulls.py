"""Redistribute phase parities using exact four-character identities on each side."""
import argparse,json,math,random
from pathlib import Path
import numpy as np
from post224_reachable_kernel import encoding,phase_vector
from post258_kernel_schedule import synth
from distributed_frame_search import native
from qiskit import qasm2

YW=[6,7,8,9,10,11,12,13,14];XW=[0,1,2,3,4,5,15,16,17]


def expand(mask,wires):return sum(((mask>>i)&1)<<b for i,b in enumerate(wires))


def identities(values):
    full=(1<<64)-1;tt=[sum(1<<i for i,v in enumerate(values) if (m&v).bit_count()%2) for m in range(512)]
    relations=set()
    for d in range(1,512):
        for diff in [False,True]:
            seen={}
            for a in range(512):
                b=a^d
                if a>b:continue
                key=tt[a]&(tt[d] if diff else full^tt[d])
                if key in seen:
                    c,e=seen[key];r={a:1,b:-1 if diff else 1,c:-1,e:1 if diff else -1}
                    if len(r)<4:continue
                    items=tuple(sorted(r.items()));factor=items[0][1]
                    relation=tuple((m,v*factor) for m,v in items);relations.add(relation)
                else:seen[key]=(a,b)
    for rel in relations:
        assert all(sum(c*(-1)**((m&v).bit_count()%2) for m,c in rel)==0 for v in values)
    return sorted(relations)


def score(co):
    masks=[m for m,c in co.items() if c and m];touch=[sum(m>>b&1 for m in masks) for b in range(18)]
    return 1.5*len(masks)+max(touch)+0.12*sum(touch)


def search(outdir,steps,seed):
    assert not outdir.exists();outdir.mkdir(parents=True);states,_=encoding()
    yvals=[sum(((states[y*64]>>b)&1)<<i for i,b in enumerate(YW)) for y in range(64)]
    xvals=[sum(((states[x]>>b)&1)<<i for i,b in enumerate(XW)) for x in range(64)]
    ids=[identities(yvals),identities(xvals)];print('identity counts',list(map(len,ids)),flush=True)
    record=json.loads(Path('artifacts/224/class_codes.json').read_text());kw=[11,12,13,14,4,15,16,17]
    co={}
    for m in record['terms']:
        sub=m;value=32//(1<<m.bit_count())
        while True:
            mask=expand(sub,kw);co[mask]=co.get(mask,0)+value*(-1)**sub.bit_count()
            if not sub:break
            sub=(sub-1)&m
    co={m:((c+16)%32)-16 for m,c in co.items() if c%32}
    cur=score(co);best=cur;initial=co.copy();rng=random.Random(seed)
    (outdir/'initial.json').write_text(json.dumps(dict(score=cur,coefficients=co),indent=2)+'\n')
    improvements=[]
    for step in range(steps):
        side=rng.randrange(2)
        if not ids[side]:continue
        rel=rng.choice(ids[side]);wires=YW if side==0 else XW;other_mask=sum(1<<b for b in (XW if side==0 else YW))
        source=rng.choice(list(co));opposite=source&other_mask
        changes=[(expand(m,wires)|opposite,c) for m,c in rel]
        occupied=[(m,c) for m,c in changes if co.get(m,0)]
        if not occupied:continue
        m,c=rng.choice(occupied);amount=-co[m]*c;new=co.copy()
        for m,c in changes:
            v=(new.get(m,0)+amount*c+16)%32-16
            if v:new[m]=v
            else:new.pop(m,None)
        value=score(new);temp=0.25+2*(1-(step%2000)/2000)
        if value<=cur or rng.random()<math.exp(min(0,(cur-value)/temp)):co,cur=new,value
        if cur<best:
            best=cur;row=dict(step=step,score=cur,support=sum(bool(m) for m in co),coefficients=co)
            improvements.append(row);(outdir/f'best_{step}.json').write_text(json.dumps(row,indent=2)+'\n');print({k:v for k,v in row.items() if k!='coefficients'},flush=True)
    # Exact modular arithmetic check on every promised state (one global phase allowed).
    delta=[]
    for state in states:
        d=sum(c*(-1)**((m&state).bit_count()%2) for m,c in co.items())-sum(c*(-1)**((m&state).bit_count()%2) for m,c in initial.items())
        delta.append(d%64)
    assert len(set(delta))==1
    (outdir/'report.json').write_text(json.dumps(dict(seed=seed,steps=steps,identities=list(map(len,ids)),improvements=improvements,final_global_phase_units=delta[0]),indent=2)+'\n')


def build(record,outdir,seeds):
    assert not outdir.exists();outdir.mkdir(parents=True);_,enc=encoding();r=json.loads(record.read_text())
    co=np.zeros(1<<18)
    for m,c in r['coefficients'].items():co[int(m)]=c*math.pi/32
    phases=co.copy();h=1
    while h<len(phases):
        b=phases.reshape(-1,2*h);a=b[:,:h].copy();c=b[:,h:].copy();b[:,:h]=a+c;b[:,h:]=a-c;h*=2
    best=(9999,9999);rows=[]
    for seed in range(seeds):
        k=native(synth(phases,seed));q=native(enc.compose(k).compose(enc.inverse()));sc=(q.depth(),q.count_ops().get('cx',0))
        row=dict(seed=seed,kernel_depth=k.depth(),depth=sc[0],cx=sc[1]);rows.append(row);print(row,flush=True)
        if sc<best:
            best=sc;path=outdir/f'feature_phase_d{sc[0]}.qasm';path.write_text(qasm2.dumps(q));row['path']=str(path)
            from exhaustive_verify import exhaustive
            exhaustive(path)
    (outdir/'report.json').write_text(json.dumps(dict(record=str(record),rows=rows),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--steps',type=int,default=20000);p.add_argument('--seed',type=int,default=0);p.add_argument('--record',type=Path);p.add_argument('--seeds',type=int,default=3);a=p.parse_args()
    if a.record:build(a.record,a.outdir,a.seeds)
    else:search(a.outdir,a.steps,a.seed)
