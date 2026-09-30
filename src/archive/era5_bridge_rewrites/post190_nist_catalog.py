"""Reproduce the NIST catalogue screen, affine witnesses and register measurements.

Run from the workspace root; public source data is cached under
artifacts/post190_nist_catalog. No network access is performed by this script.
These are component experiments, NOT improved full logo oracles.
"""
def screen():
 import sys,re,json,numpy as np,time
 sys.path.insert(0,'src')
 from post190_degree_rank_bound import targets
 from pathlib import Path
 p=Path('artifacts/post190_nist_catalog')
 def walsh(a):
  a=np.array(a,dtype=np.int16,copy=True)
  for bit in range(6):
   v=a.reshape(-1,2,1<<bit); l=v[:,0,:].copy();r=v[:,1,:].copy();v[:,0,:]=l+r;v[:,1,:]=l-r
  return a
 monos={}
 for m in range(64):
  s=''.join('x'+str(i+1) for i in range(6) if m>>i&1) or '1'
  monos[s]=sum(1<<x for x in range(64) if x&m==m)
 monos['0']=0
 blocks=(p/'n6_circ.txt').read_text().strip().split('\n\n')
 reps=[]
 for b in blocks:
  v=0
  for m in b.splitlines()[0].split('+'):v^=monos[m]
  reps.append(v)
 a=np.array([[(v>>i)&1 for i in range(64)] for v in reps],dtype=np.int16)
 w=walsh(1-2*a); sig=np.sort(abs(w),axis=1)
 r={}
 for side,ts in targets().items():
  for i,t in enumerate(ts):
   tw=walsh(1-2*np.array(t)); matches=np.where(np.all(sig==np.sort(abs(tw)),axis=1))[0].tolist()
   print(side,i,len(matches),flush=True)
   r[f'{side}{i}']={'target':list(map(int,t)),'walsh':tw.tolist(),'candidates':[{'index':j,'truth':reps[j],'walsh':w[j].tolist(),'block':blocks[j]} for j in matches]}
 (p/'matches.json').write_text(json.dumps(r,indent=2))

def map_functions():
 import json,time
 from pathlib import Path
 p=Path('artifacts/post190_nist_catalog');data=json.loads((p/'matches.json').read_text())
 phase=[[sum(1<<v for v in range(128) if (((v&63)&u).bit_count()^(v>>6))&1==s) for s in range(2)] for u in range(64)]
 def match(t,r,limit=200000):
  nodes=0
  def rec(images,allowed,c):
   nonlocal nodes
   nodes+=1
   if nodes>limit:raise TimeoutError
   n=len(images)
   if n==64:return images,allowed,c
   for v in range(1,64):
    if v in images:continue
    new=[x^v for x in images];ok=allowed
    for i,x in enumerate(new,n):
     a=t[i];b=r[x^c]
     if abs(a)!=abs(b):ok=0;break
     if a:ok &=phase[i][int((a<0)!=(b<0))]
     if not ok:break
    if ok:
     z=rec(images+new,ok,c)
     if z:return z
   return None
  for c in range(64):
   if abs(t[0])!=abs(r[c]):continue
   allowed=(1<<128)-1
   if t[0]:allowed&=phase[0][int((t[0]<0)!=(r[c]<0))]
   z=rec([0],allowed,c)
   if z:return z,nodes
  return None,nodes
 out={}
 for key in ['y2','x1','y0','x0','x2','y1']:
  start=time.monotonic()
  for cand in data[key]['candidates']:
   try:z,n=match(data[key]['walsh'],cand['walsh'],50000)
   except TimeoutError:continue
   if z:
    images,allowed,c=z;v=(allowed&-allowed).bit_length()-1
    # Walsh relation T[u]=(-1)^(b.u+e) R[M u+c]. Invert transpose M.
    cols=[images[1<<i] for i in range(6)];b=v&63;e=v>>6
    def mt(x):return sum(((col&x).bit_count()%2)<<i for i,col in enumerate(cols))
    inv={mt(x):x for x in range(64)}
    assert len(inv)==64
    pred=[]
    for x in range(64):
     zarg=inv[x^b];pred.append(((cand['truth']>>zarg)&1)^((c&zarg).bit_count()%2)^e)
    assert pred==data[key]['target']
    out[key]={'representative':cand['index'],'block':cand['block'],'input_map':[inv[x^b] for x in range(64)],'output_linear_on_rep':c,'output_constant':e,'nodes':n,'seconds':time.monotonic()-start}
    print(key,'FOUND',cand['index'],n,time.monotonic()-start,flush=True);break
  else:print(key,'NO MATCH within budgets',flush=True)
  (p/'affine_maps.json').write_text(json.dumps(out,indent=2))

def extract():
 import json,re,sys
 from pathlib import Path
 sys.path.insert(0,'src')
 from post190_xag_inplace_lower import outputs
 from post190_degree_rank_bound import targets
 p=Path('artifacts/post190_nist_catalog');maps=json.loads((p/'affine_maps.json').read_text())
 import gzip
 archive=gzip.decompress((p/'n6_slp_mc5.txt.gz').read_bytes()).decode()
 lookup={frozenset(v['block'].splitlines()[0].split('+')):k for k,v in maps.items()}
 for block in archive.strip().split('\n\n'):
  first=block.splitlines()[0]
  if ' = ' in first and frozenset(first.split(' = ')[1].split('+')) in lookup:
   key=lookup[frozenset(first.split(' = ')[1].split('+'))]
   (p/(key+'_source.slp')).write_text(block)
 for key,item in maps.items():
  lines=(p/(key+'_source.slp')).read_text().splitlines(); top=[re.search(r'= \((.*?)\) \* \((.*?)\)',l).groups() for l in lines if re.match(r'a\d+ =',l)];k=len(top)
  def aff(s):
   c=0;mask=0
   for t in s.split('+'):
    if t=='1':c^=1
    elif t.startswith('x'):mask^=1<<(int(t[1:])-1)
   truth=[c^((mask&x).bit_count()%2) for x in item['input_map']]
   base=truth[0];a=[i for i in range(6) if truth[1<<i]^base]
   assert all(truth[x]==base^(sum(x>>i&1 for i in a)%2) for x in range(64))
   a += [6+int(t[1:]) for t in s.split('+') if t.startswith('a')]
   return a,bool(base)
  gates=[]
  for j,(l,r) in enumerate(top):
   ab=[]
   for z,s in enumerate([l,r]):
    a,c=aff(s)
    ab.append((a,c))
   gates.append(dict(a=ab[0],b=ab[1]))
  a,c=aff(lines[-1].split('=')[1].strip())
  # Extra output affine on representative coordinates.
  mask=item['output_linear_on_rep'];values=[(mask&x).bit_count()%2 for x in item['input_map']];c^=bool(values[0]^item['output_constant'])
  for i in range(6):
   if values[1<<i]^values[0]:
    if i in a:a.remove(i)
    else:a.append(i)
  w={'k':k,'gates':gates,'outs':[(a,c)]}
  assert all(outputs(w,x)==[targets()[key[0]][int(key[1])][x]] for x in range(64)),key
  (p/(key+'_witness.json')).write_text(json.dumps(w,indent=2));print(key,k,'VERIFIED',flush=True)

def merge():
 import json,sys
 from pathlib import Path
 sys.path.insert(0,'src')
 from post190_xag_inplace_lower import outputs
 p=Path('artifacts/post190_nist_catalog')
 for side in ['x','y']:
  signals=[(1<<64)-1]+[sum(1<<x for x in range(64) if x>>i&1) for i in range(6)];gates=[];outs=[]
  def resolve(v):
   piv={}
   for i,t in enumerate(signals):
    s=1<<i
    while t:
     b=t.bit_length()-1
     if b in piv:t^=piv[b][0];s^=piv[b][1]
     else:piv[b]=(t,s);break
   s=0
   while v:
    b=v.bit_length()-1
    if b not in piv:return None
    v^=piv[b][0];s^=piv[b][1]
   return ([i-1 for i in range(1,len(signals)) if s>>i&1],bool(s&1))
  for bit in range(3):
   w=json.loads((p/(side+str(bit)+'_witness.json')).read_text());local=signals[1:7].copy()
   def val(form):
    v=((1<<64)-1) if form[1] else 0
    for i in form[0]:v^=local[i]
    return v
   for g in w['gates']:
    a=val(g['a']);b=val(g['b']);v=a&b
    if resolve(v) is None:gates.append({'a':resolve(a),'b':resolve(b)});signals.append(v)
    local.append(v)
   outs.append(resolve(val(w['outs'][0])))
  w={'k':len(gates),'gates':gates,'outs':outs}
  from post190_degree_rank_bound import targets
  assert all(outputs(w,x)==[t[x] for t in targets()[side]] for x in range(64))
  (p/(side+'_merged_witness.json')).write_text(json.dumps(w,indent=2));print(side,len(gates),flush=True)

def measure():
 import sys,json,time
 from pathlib import Path
 sys.path.insert(0,'src')
 from post190_xag_register_schedule import search,lower,verify
 from qiskit import qasm2
 p=Path('artifacts/post190_nist_catalog');reports={}
 for key in ['y0','y1','y2','x0','x1','x2']:
  w=json.loads((p/(key+'_witness.json')).read_text());w['outs'] += [([],False),([],False)]
  r=search(w)
  if r['status']=='found':
   q=lower(w,r);r['verification']=verify(w,q);(p/(key+'_9wire.qasm')).write_text(qasm2.dumps(q))
  reports[key]=r;print(key,{k:v for k,v in r.items() if k!='path'},flush=True)
  (p/'measurements.json').write_text(json.dumps(reports,indent=2))

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['screen','map','extract','merge','measure']);a=p.parse_args()
 {'screen':screen,'map':map_functions,'extract':extract,'merge':merge,'measure':measure}[a.stage]()
