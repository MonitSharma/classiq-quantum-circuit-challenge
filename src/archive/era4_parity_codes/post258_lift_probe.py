"""Enumerate level-wise signed Ry lifts in 28 unordered linear code frames.

This is a spectral diagnostic only; it does not assert native circuit depth.
"""
import sys,itertools,json
sys.path.insert(0,'src')
import numpy as np
import level_oracle as l
from distributed_ucry import walsh
from distributed_frame_search import transformed,FRAMES
from level_encoder_search_fast import CODES
H=np.array([[(-1)**((a&b).bit_count()%2) for b in range(64)] for a in range(64)],int)
rows=[]
for side in ['u','v']:
 results=[]
 for frame in FRAMES:
  if tuple(sorted(frame))!=frame: continue
  triple=transformed(CODES[0][side=='v'],frame)
  counts=[]; settings=[]
  for subset in triple:
   a,b=[np.array([(subset>>k)&1 for k in l.LEVEL[side+str(p)]]) for p in (1,2)]
   # Independent sign per level that is marked: 2^k choices, exact integer lifts.
   opts=[]
   for p,t in enumerate([a,b],1):
    levels=[k for k in range(6) if subset>>k&1]
    vals=[]
    for signs in itertools.product([-1,1],repeat=len(levels)):
     tab=t.copy()
     for k,sg in zip(levels,signs): tab[np.array(l.LEVEL[side+str(p)])==k]*=sg
     vals.append((H@tab,tab,signs))
    opts.append(vals)
   best=None
   for sa,ta,ga in opts[0]:
    for sb,tb,gb in opts[1]:
     c=[int(np.count_nonzero(z)) for z in [sa,sb-sa,sb]]
     score=sum(c)
     if best is None or score<best[0]: best=(score,c,ta.tolist(),tb.tolist(),ga,gb)
   counts.append(best[1]);settings.append(best[2:])
  results.append(dict(frame=frame,triple=triple,total=sum(map(sum,counts)),counts=counts,lifts=settings))
 results.sort(key=lambda r:r['total'])
 print(side,[(r['frame'],r['total'],r['counts']) for r in results[:3]],flush=True)
 rows.append(dict(side=side,results=results))
from pathlib import Path
out=Path('artifacts/post258_lift_probe.json')
if out.exists():
 assert json.loads(out.read_text())==rows, 'Refusing to overwrite different results'
else:
 out.write_text(json.dumps(rows,indent=2)+'\n')
