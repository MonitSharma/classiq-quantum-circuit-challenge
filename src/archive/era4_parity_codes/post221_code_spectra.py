"""Enumerate constant-cell scalar code bits before choosing a complete encoding."""
import json,itertools
from pathlib import Path
import numpy as np
from post258_raw_parity_codes import cells
from distributed_ucry import rank
import two_stage_oracle as ts
H=np.array([[(-1)**((a&b).bit_count()%2) for b in range(64)] for a in range(64)],int)

def options(cls,mask):
 cc=cells(cls,mask);keys=list(cc);groups=[[i for i,k in enumerate(keys) if k[0]==b] for b in [0,1]]
 fixed=[g[0] for g in groups];free=[i for i in range(len(keys)) if i not in fixed];opts=[]
 pairs=[(a,b) for g in groups for a,b in itertools.combinations(g,2)]
 for z in range(1<<len(free)):
  bits=[0]*len(keys)
  for i,b in enumerate(free):bits[b]=z>>i&1
  if any(not len(g)-4<=sum(bits[i] for i in g)<=4 for g in groups):continue
  truth=np.zeros(64,dtype=int)
  for i,k in enumerate(keys):truth[cc[k]]=bits[i]
  sp=H@truth;support=np.flatnonzero(sp);sep=sum((bits[a]^bits[b])<<i for i,(a,b) in enumerate(pairs))
  opts.append(dict(bits=bits,truth=truth.tolist(),support=len(support),rank=rank([int(m) for m in support]),sep=sep))
 opts.sort(key=lambda o:(o['support'],o['rank']))
 return keys,pairs,opts

if __name__=='__main__':
 out=Path('artifacts/post221_code_spectra_v1');assert not out.exists();out.mkdir()
 for side,cls,mask in [('y',ts.ROWCLS,32),('x',ts.COLCLS,48)]:
  keys,pairs,opts=options(cls,mask);full=(1<<len(pairs))-1;best=999;triples=[]
  for i,a in enumerate(opts):
   if a['support']*3>best+12:break
   for j in range(i+1,len(opts)):
    b=opts[j]
    if a['support']+b['support']*2>best+12:break
    missing=full^(a['sep']|b['sep'])
    for k in range(j+1,len(opts)):
     c=opts[k];score=a['support']+b['support']+c['support']
     if score>best+12:break
     if missing&~c['sep']:continue
     if score<best:best=score;print(side,'best',best,[v['support'] for v in [a,b,c]],flush=True)
     triples.append((score,i,j,k))
  triples.sort();triples=[t for t in triples if t[0]<=best+12][:500]
  (out/f'{side}.json').write_text(json.dumps(dict(keys=keys,mask=mask,options=opts,triples=triples),indent=2)+'\n')
  print(side,'scalar options',len(opts),'triples kept',len(triples),flush=True)
