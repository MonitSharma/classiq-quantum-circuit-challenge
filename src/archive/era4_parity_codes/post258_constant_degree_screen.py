"""Exact constant-per-class degree screen; this does not bound split encoders."""
import argparse,itertools,json
from pathlib import Path
from post258_raw_parity_codes import cells
import two_stage_oracle as ts


def run(outdir):
    assert not outdir.exists();outdir.mkdir(parents=True);rows=[]
    for side,cls,mask in [('y',ts.ROWCLS,32),('x',ts.COLCLS,48),('x',ts.COLCLS,16)]:
        cc=cells(cls,mask);keys=list(cc);valid=[]
        for assignment in range(1<<len(keys)):
            vals=[0]*64
            for k,key in enumerate(keys):
                for v in cc[key]:vals[v]=assignment>>k&1
            for b in range(6):
                for w in range(64):
                    if w>>b&1:vals[w]^=vals[w^(1<<b)]
            if all(not vals[w] for w in range(64) if w.bit_count()>4):valid.append(assignment)
        pairs=[(i,j) for i in range(len(keys)) for j in range(i) if keys[i][0]==keys[j][0]]
        covers={v:sum(1<<k for k,(i,j) in enumerate(pairs) if (v>>i^v>>j)&1) for v in valid}
        full=(1<<len(pairs))-1
        witnesses=[(a,b,c) for a,b,c in itertools.combinations(valid,3) if covers[a]|covers[b]|covers[c]==full]
        row=dict(side=side,raw_mask=mask,degree_limit=4,cells=keys,scalar_assignments=valid,scalar_space_size=len(valid),separating_triples=len(witnesses),witnesses=witnesses)
        rows.append(row);print(side,mask,len(valid),len(witnesses),flush=True)
    (outdir/'report.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();run(a.outdir)
