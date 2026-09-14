"""Output-degree filtration lower bound for shared XOR/AND circuits.

An output of the j-th AND has algebraic degree <= j+1 (degree bound).
For d>=2, the first d-2 ANDs have no degree>=d terms. Consequently a k-AND
circuit's outputs have projected rank <= max(0,k-d+2), hence k>=r+d-2
when that rank r is positive. Applies to fixed Boolean output functions.
"""
import json,itertools
from pathlib import Path
from post258_two_stage_anf import decode
from two_stage_oracle import ROWCLS,COLCLS
from post190_xag_inplace_lower import rank

def targets():
 c=json.loads(Path('artifacts/190/class_codes.json').read_text());out={}
 for side,cls,mask in [('y',ROWCLS,32),('x',COLCLS,48)]:
  lab=decode(c[side+'lab']);v=[lab[((i&mask).bit_count()%2,int(z))] for i,z in enumerate(cls)]
  out[side]=[[(z>>b)&1 for z in v] for b in range(3)]
 return out

def certificate(table):
 anf=[]
 for values in table:
  a=values.copy()
  for b in range(6):
   for m in range(64):
    if m>>b&1:a[m]^=a[m^(1<<b)]
  anf.append(a)
 rows=[]
 for d in range(2,7):
  masks=[m for m in range(64) if m.bit_count()>=d]
  vectors=[sum(a[m]<<j for j,m in enumerate(masks)) for a in anf];r=rank(vectors)
  rows.append(dict(min_degree=d,rank=r,AND_lower_bound=d-2+r if r else 0,monomial_masks=masks,coefficient_vectors=vectors))
 return dict(bound=max(r['AND_lower_bound'] for r in rows),rows=rows,anf=anf)

if __name__=='__main__':
 r={side:certificate(t) for side,t in targets().items()}
 p=Path('artifacts/post190_inplace_xag_lower/degree_rank_certificate.json');p.write_text(json.dumps(r,indent=2));print({k:v['bound'] for k,v in r.items()})
