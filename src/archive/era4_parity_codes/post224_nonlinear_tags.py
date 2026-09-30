"""Enumerate reversible rank-two quadratic tags and low-degree class codes."""
import argparse,itertools,json
from pathlib import Path
import two_stage_oracle as ts

FULL=(1<<64)-1
PAR=[sum(1<<v for v in range(64) if (v&m).bit_count()%2) for m in range(64)]


def null_basis(rows,n):
    piv={}
    for row in rows:
        while row:
            p=row.bit_length()-1
            if p in piv:row^=piv[p]
            else:piv[p]=row;break
    result=[]
    for free in range(n):
        if free in piv:continue
        v=1<<free
        for p in sorted(piv):
            if (piv[p]&v).bit_count()%2:v^=1<<p
        assert all(not (row&v).bit_count()%2 for row in rows)
        result.append(v)
    return result


def codes_for(cells,degree):
    keys=list(cells);rows=[]
    for m in range(64):
        if m.bit_count()<=degree:continue
        rows.append(sum((sum(v&~m==0 for v in cells[k])%2)<<i for i,k in enumerate(keys)))
    basis=null_basis(rows,len(keys));pairs=[(i,j) for i in range(len(keys)) for j in range(i) if keys[i][0]==keys[j][0]]
    full=(1<<len(pairs))-1;span={0:0}
    for v in basis:
        cv=sum(((v>>i^v>>j)&1)<<k for k,(i,j) in enumerate(pairs))
        for old,assignment in list(span.items()):span.setdefault(old^cv,assignment^v)
    available=list(span)
    for i,a in enumerate(available):
        for j in range(i):
            b=available[j];missing=full^(a|b)
            for c in available[:j]:
                if c&missing==missing:
                    assignments=[span[a],span[b],span[c]];labels=[0]*64
                    for k,key in enumerate(keys):
                        code=sum(((v>>k)&1)<<bit for bit,v in enumerate(assignments))
                        for v in cells[key]:labels[v]=code
                    return labels,len(basis),len(span)
    return None,len(basis),len(span)


def run(outdir,side):
    assert not outdir.exists();outdir.mkdir(parents=True);cls=ts.ROWCLS if side=='y' else ts.COLCLS
    seen=set();viable=[];witnesses=[];stats={'tags':0,'viable':0,'degree3':0,'degree4':0}
    for target in range(6):
        forms=[m for m in range(1,64) if not m>>target&1]
        planes=sorted({tuple(sorted((a,b,a^b))) for a in forms for b in forms if a<b})
        for plane in planes:
            a,b=plane[:2];product=PAR[a]&PAR[b]
            for linear in [0]+forms:
                tag=PAR[1<<target]^PAR[linear]^product
                if tag in seen:continue
                seen.add(tag);stats['tags']+=1;cells={}
                for v,c in enumerate(cls):cells.setdefault((tag>>v&1,c),[]).append(v)
                counts=[sum(k[0]==bit for k in cells) for bit in [0,1]]
                if max(counts)>8:continue
                stats['viable']+=1;entry=dict(target=target,a=a,b=b,linear=linear,tag=str(tag),counts=counts)
                for degree in [3,4]:
                    labels,dimension,classes=codes_for(cells,degree)
                    if labels is not None:
                        stats[f'degree{degree}']+=1;entry.update(degree=degree,labels=labels,dimension=dimension,quotient=classes);witnesses.append(entry)
                        print('witness',side,{k:v for k,v in entry.items() if k!='labels'},flush=True);break
                viable.append(entry)
        print('target complete',side,target,stats,flush=True)
        (outdir/'report.json').write_text(json.dumps(dict(side=side,stats=stats,witnesses=witnesses,viable=viable),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--side',choices=['x','y'],required=True);a=p.parse_args();run(a.outdir,a.side)
