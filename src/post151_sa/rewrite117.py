"""Whole-oracle CNOT bridge search, scored by native depth and critical paths.

Every rewrite is an exact full-operator identity. Existing artifacts are read-only.
"""
import argparse, hashlib, json, math, random, time
from pathlib import Path
from postopt import parse_ops, fuse, depth, write
from canc import tag, com, simplify


def moves(ops):
    tagged=[tag(o) for o in ops]
    out=[]
    for i,a in enumerate(tagged):
        if a[0]!='cx': continue
        for direction,indices in [('right',range(i+1,len(ops))),('left',range(i-1,-1,-1))]:
            for j in indices:
                b=tagged[j]
                if com(a,b): continue
                if b[0]=='cx' and len(set(a[1]+b[1]))==3:
                    out.append((min(i,j),max(i,j),direction))
                break
    return out


def rewrite(ops,move):
    i,j,direction=move
    a,b=ops[i],ops[j]
    assert a[0]==b[0]=='cx'
    c,t=a[1]; u,v=b[1]
    middle=(c,v) if t==u else (u,t)
    assert t==u or v==c
    moving=tag(a if direction=='right' else b)
    assert all(com(moving,tag(o)) for o in ops[i+1:j])
    at=j if direction=='right' else i
    result=[]
    for k,o in enumerate(ops):
        if k==at: result.extend([b,('cx',middle,None),a])
        if k not in (i,j): result.append(o)
    return fuse(simplify(result,verbose=False))


def graph(ops):
    tagged=[tag(o) for o in ops]; n=len(ops)
    succ=[set() for _ in ops]; pred=[set() for _ in ops]; last=[[] for _ in range(18)]
    for j,b in enumerate(tagged):
        for w in b[1]:
            for i in last[w]:
                if i not in pred[j] and not com(tagged[i],b):
                    succ[i].add(j); pred[j].add(i)
            last[w].append(j)
    # Transitive reduction also gives precedence tails.
    reach=[0]*n; red=[[] for _ in ops]; rp=[[] for _ in ops]
    for i in range(n-1,-1,-1):
        for j in sorted(succ[i]):
            if not (reach[i]>>j)&1:
                red[i].append(j); rp[j].append(i); reach[i]|=(1<<j)|reach[j]
    tails=[1]*n
    for i in range(n-1,-1,-1):
        if red[i]: tails[i]+=max(tails[j] for j in red[i])
    return red,rp,tails


def scheduled(ops,g,seed):
    succ,pred,tails=g; rng=random.Random(seed)
    cnt=list(map(len,pred)); ready={i for i in range(len(ops)) if not cnt[i]}
    result=[]; noise=[0,.2,1,2][seed%4]
    while ready:
        rank=sorted(ready,key=lambda i:(tails[i]+noise*rng.random(),-i),reverse=True)
        used=0; layer=[]
        for i in rank:
            mask=sum(1<<w for w in ops[i][1])
            if not used&mask: used|=mask; layer.append(i)
        ready.difference_update(layer)
        result.extend(ops[i] for i in layer)
        for i in layer:
            for j in succ[i]:
                cnt[j]-=1
                if not cnt[j]: ready.add(j)
    assert len(result)==len(ops)
    return fuse(simplify(result,verbose=False))


def score(ops):
    wt=[0]*18; starts=[]
    for o in ops:
        s=max(wt[w] for w in o[1]); starts.append(s)
        for w in o[1]: wt[w]=s+1
    d=max(wt); wt=[0]*18; critical=0; near=0
    for i in range(len(ops)-1,-1,-1):
        o=ops[i]; t=max(wt[w] for w in o[1])+1
        critical+=starts[i]+t==d
        near+=max(0,starts[i]+t-d+3)
        for w in o[1]: wt[w]=t
    return d,critical,near


def optimized(ops,move,seeds=3):
    cand=rewrite(ops,move); best=cand; bs=score(best)
    g=graph(cand)
    for s in range(seeds):
        x=scheduled(cand,g,s); sc=score(x)
        if sc<bs: best,bs=x,sc
    return best,bs


def run(a):
    out=Path(a.outdir); out.mkdir(parents=True,exist_ok=True)
    ops=fuse(parse_ops(a.source)); base=score(ops); ms=moves(ops)
    rows=[]; pool=[]; start=time.monotonic()
    print('BASE',base,'moves',len(ms),flush=True)
    for k,m in enumerate(ms):
        cand,sc=optimized(ops,m,a.schedules)
        row={'index':k,'move':m,'score':sc,'cx':sum(o[0]=='cx' for o in cand)}; rows.append(row)
        pool.append((sc,k,cand)); pool.sort(key=lambda v:(v[0],v[1])); pool=pool[:a.keep]
        if sc[0]<base[0]:
            path=out/f'improve_{k}_d{sc[0]}.qasm'; write(cand,path); print('IMPROVED',path,sc,flush=True)
        if k%50==0: print(k,'/',len(ms),'best',pool[0][:2],'elapsed',round(time.monotonic()-start),flush=True)
    for sc,k,cand in pool:
        path=out/f'candidate_{k}_d{sc[0]}.qasm'; write(cand,path); rows[k]['path']=str(path)
    report={'source':a.source,'source_sha256':hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),'base':base,'seconds':time.monotonic()-start,'rows':rows,'retained':[r for r in rows if 'path' in r]}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('DONE',len(ms),'best',pool[0][:2],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('source'); p.add_argument('outdir'); p.add_argument('--schedules',type=int,default=3); p.add_argument('--keep',type=int,default=20); run(p.parse_args())
