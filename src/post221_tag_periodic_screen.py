"""Exact constant-cell affine-period screen for reversible quadratic raw tags."""
import itertools,json,argparse
from pathlib import Path
from distributed_ucry import rank
import two_stage_oracle as ts

def screen(cls,entry):
 tag=int(entry['tag']);keys=list(dict.fromkeys((tag>>v&1,c) for v,c in enumerate(cls)));idx={k:i for i,k in enumerate(keys)};nodes=[idx[(tag>>v&1,c)] for v,c in enumerate(cls)];n=len(keys)
 groups=[[i for i,k in enumerate(keys) if k[0]==b] for b in [0,1]];pairs=[(a,b) for g in groups for a,b in itertools.combinations(g,2)];full=(1<<len(pairs))-1;opts={}
 for d in range(1,64):
  for flip in [0,1]:
   edges=[[] for _ in range(n)]
   for v in range(64):a,b=nodes[v],nodes[v^d];edges[a].append(b);edges[b].append(a)
   parity=[None]*n;components=[];bad=False
   for a in range(n):
    if parity[a] is not None:continue
    parity[a]=0;comp=[a]
    for b in comp:
     for c in edges[b]:
      if parity[c] is None:parity[c]=parity[b]^flip;comp.append(c)
      elif parity[c]!=(parity[b]^flip):bad=True
    components.append(comp)
   if bad:continue
   for assignment in range(1<<(len(components)-1)):
    bits=parity.copy()
    for i,comp in enumerate(components[1:]):
     if assignment>>i&1:
      for b in comp:bits[b]^=1
    if any(not len(g)-4<=sum(bits[i] for i in g)<=4 for g in groups):continue
    key=tuple(bits)
    if key not in opts:opts[key]=dict(bits=bits,truth=[bits[nodes[v]] for v in range(64)],sep=sum((bits[a]^bits[b])<<i for i,(a,b) in enumerate(pairs)),periods=[])
    opts[key]['periods'].append((d,flip))
 vals=list(opts.values());solutions=[]
 for a,b,c in itertools.combinations(vals,3):
  if a['sep']|b['sep']|c['sep']!=full:continue
  periods=next((ds for ds in itertools.product(a['periods'],b['periods'],c['periods']) if rank([p[0] for p in ds])==3),None)
  if periods:
   solutions.append(dict(labels=[a['truth'][v]|b['truth'][v]<<1|c['truth'][v]<<2 for v in range(64)],periods=periods));break
 return len(vals),solutions

def run(side):
 out=Path(f'artifacts/post221_tag_periodic_{side}_v1');assert not out.exists();out.mkdir();cls=ts.ROWCLS if side=='y' else ts.COLCLS;r=json.loads(Path(f'artifacts/post224_nonlinear_tags_{side}_v1/report.json').read_text());rows=[]
 for entry in r['viable']:
  count,solutions=screen(cls,entry);row=dict(**entry,periodic_scalar_count=count,solutions=solutions);rows.append(row)
  if solutions:print('witness',side,row,flush=True)
 (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print(side,'tags',len(rows),'scalarmax',max(r['periodic_scalar_count'] for r in rows),'witnesses',sum(bool(r['solutions']) for r in rows),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--side',choices=['y','x'],required=True);run(p.parse_args().side)
