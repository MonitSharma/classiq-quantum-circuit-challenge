"""Exact finite spectral screen of normalized injective six-level codebooks.

Enumerates all unordered bit triples with code(0)=0. Complement and output
permutation freedoms are quotiented for endpoint support, not claimed irrelevant
to full native depth. No quantum artifacts or best circuits are overwritten.
"""
import itertools
import json
from pathlib import Path
import numpy as np
from level_oracle import LEVEL, code_of
from distributed_ucry import walsh


def run():
    records=[]
    books=[]
    for triple in itertools.combinations(range(2,64,2),3):
        codes=code_of(triple,LEVEL['u1'])[0]
        if len(set(codes))==6: books.append(triple)
    for side in ['u','v']:
        counts={};spectra={}
        for subset in range(2,64,2):
            a,b=[np.array([(subset>>v)&1 for v in LEVEL[side+str(p)]]) for p in (1,2)]
            counts[subset]=[int(np.count_nonzero(abs(walsh([v]))>1e-12)) for v in [a,b-a,-b]]
            spectra[subset]=[np.rint(walsh([v])[0]*64).astype(int) for v in [a,b]]
        rows=[]
        for triple in books:
            stages=[sum(counts[s][p] for s in triple) for p in range(3)]
            rows.append(dict(triple=triple,stages=stages,total=sum(stages)))
        rows.sort(key=lambda r:r['total'])
        # Independent pass codebooks. Best assignment of physical output bits
        # uses one of six pairings, exactly scored by middle Walsh differences.
        best=None
        for t1 in books:
            start=sum(counts[s][0] for s in t1)
            for t2 in books:
                end=sum(counts[s][2] for s in t2)
                if best is not None and start+end >=best['total']:continue
                for perm in itertools.permutations(t2):
                    middle=sum(int(np.count_nonzero(spectra[b][1]-spectra[a][0])) for a,b in zip(t1,perm))
                    total=start+middle+end
                    if best is None or total<best['total']:
                        best=dict(first=t1,second=perm,stages=[start,middle,end],total=total)
        result=dict(side=side,codebooks=len(books),same_codebook_top=rows[:20],independent_pass_best=best)
        records.append(result);print(result,flush=True)
    out=Path('artifacts/post258_codebook_screen.json')
    assert not out.exists()
    out.write_text(json.dumps(records,indent=2)+'\n')

if __name__=='__main__':run()
