"""Joint nine-wire reversible search with free class labels.

New output descriptors are accepted only after all 64 inputs are checked.
No affine output gauge is fixed: its native gate cost is not free.
"""
import argparse,json,time,random
from pathlib import Path
import numpy as np
import z3
from post190_register_encoder import select,build
from two_stage_oracle import ROWCLS,COLCLS
from qiskit import qasm2
from qiskit.quantum_info import Statevector
from distributed_frame_search import native

def solve(side,samples,stages=4,cx_layers=2,seconds=15,classes=None,split=False,constant=True):
 n=9;size=len(samples);s=z3.Solver();s.set(timeout=int(seconds*1000))
 state=[z3.BitVecVal(sum(((v>>w)&1)<<i for i,v in enumerate(samples)),size) for w in range(6)]+[z3.BitVecVal(0,size)]*3
 specs=[]
 def perm(name,group):
  p=[z3.BitVec(f'{name}_{i}',4) for i in range(n)]
  for v in p:s.add(z3.ULT(v,n))
  s.add(z3.Distinct(p))
  for j in range(1,n//group):s.add(z3.ULT(p[(j-1)*group+group-1],p[j*group+group-1]))
  if group==3:
   for j in range(3):s.add(z3.ULT(p[3*j],p[3*j+1]))
  return p
 def xlayer(name):
  nonlocal state
  on=[z3.Bool(f'{name}_{i}') for i in range(n)]
  state=[z3.If(b,~v,v) for b,v in zip(on,state)];specs.append(('x',None,on))
 xlayer('initial')
 for stage in range(stages+1):
  for gap in range(cx_layers):
   p=perm(f'cx_{stage}_{gap}',2);on=[z3.Bool(f'cxon_{stage}_{gap}_{i}') for i in range(4)]
   old=state;controls=[select(old,p[2*i]) for i in range(4)];state=[]
   for w in range(n):
    v=old[w]
    for i in range(4):v=z3.If(z3.And(on[i],p[2*i+1]==w),old[w]^controls[i],v)
    state.append(v)
   specs.append(('cx',p,on))
  if stage==stages:break
  p=perm(f'ccx_{stage}',3);on=[z3.Bool(f'ccxon_{stage}_{i}') for i in range(3)]
  old=state;products=[select(old,p[3*i])&select(old,p[3*i+1]) for i in range(3)];state=[]
  for w in range(n):
   v=old[w]
   for i in range(3):v=z3.If(z3.And(on[i],p[3*i+2]==w),old[w]^products[i],v)
   state.append(v)
  specs.append(('ccx',p,on))
 xlayer('final')
 from two_stage_oracle import ROWCLS,COLCLS
 if classes is None:classes=ROWCLS if side=='y' else COLCLS
 rawmask,rawwire=(32,5) if side=='y' else (48,4)
 code=[z3.Concat(*[z3.Extract(i,i,state[w]) for w in (8,7,6,rawwire)]) for i in range(size)]
 if split:
  s.add(state[rawwire]==z3.BitVecVal(sum(((v&rawmask).bit_count()%2)<<i for i,v in enumerate(samples)),size))
 if constant:
  representatives={}
  for i,v in enumerate(samples):
   key=(classes[v],(v&rawmask).bit_count()%2) if split else classes[v]
   if key in representatives:s.add(code[i]==representatives[key])
   else:representatives[key]=code[i]
  s.add(z3.Distinct(list(representatives.values())))
 else:
  for i,a in enumerate(samples):
   for j,b in enumerate(samples[:i]):
    if classes[a]!=classes[b]:s.add(code[i]!=code[j])
 start=time.time();status=s.check();row=dict(side=side,status=str(status),seconds=time.time()-start,samples=len(samples),stages=stages,cx_layers=cx_layers,depth_ceiling=2+9*stages+(stages+1)*cx_layers,split=split,class_constant=constant)
 if status!=z3.sat:
  if status==z3.unknown:row['reason']=s.reason_unknown()
  return row,None
 m=s.model();ops=[]
 for kind,p,on in specs:
  order=list(range(n)) if p is None else [m.eval(v).as_long() for v in p];width={'x':1,'cx':2,'ccx':3}[kind]
  for i,b in enumerate(on):
   if z3.is_true(m.eval(b,model_completion=True)):ops.append((kind,order[width*i:width*(i+1)]))
 row['ops']=ops
 return row,ops

def evaluate(ops,side,classes=None,split=False,constant=True):
 if classes is None:classes=ROWCLS if side=='y' else COLCLS
 words=list(range(64))
 for kind,ws in ops:
  for i,v in enumerate(words):
   if kind=='x':words[i]=v^(1<<ws[0])
   elif kind=='cx':words[i]=v^(((v>>ws[0])&1)<<ws[1])
   else:words[i]=v^((((v>>ws[0])&(v>>ws[1]))&1)<<ws[2])
 rawmask,rawwire=(32,5) if side=='y' else (48,4)
 codes=[((v>>rawwire)&1)|(((v>>6)&7)<<1) for v in words]
 bad=set()
 for a in range(64):
  if split and (codes[a]&1)!=(a&rawmask).bit_count()%2:bad.add(a)
  for b in range(a):
   if classes[a]!=classes[b] and codes[a]==codes[b]:bad.update([a,b])
   elif constant and classes[a]==classes[b] and (not split or (a&rawmask).bit_count()%2==(b&rawmask).bit_count()%2) and codes[a]!=codes[b]:bad.update([a,b])
 return sorted(bad),words,codes


def verify(ops,words,codes):
 q=build(ops);full=q.copy();full.z(6);full.compose(q.inverse(),inplace=True);full=native(full)
 phase=None;error=0.
 for x in range(64):
  s=Statevector.from_int(x,512);v=s.evolve(q).data
  assert abs(abs(v[words[x]])-1)<1e-10
  v=s.evolve(full).data;sign=(-1)**((codes[x]>>1)&1)
  if phase is None:phase=v[x]/sign
  want=np.zeros(512,complex);want[x]=phase*sign;error=max(error,float(np.max(abs(v-want))))
 assert error<1e-10
 return q,dict(depth=q.depth(),cx=q.count_ops().get('cx',0),width=9,checked_inputs=64,phase_inverse_error=error)


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--stages',type=int,default=4);p.add_argument('--seconds',type=float,default=20);p.add_argument('--samples',type=int,default=64);p.add_argument('--split',action='store_true');p.add_argument('--loose',action='store_true');a=p.parse_args()
 assert not a.outdir.exists();a.outdir.mkdir(parents=True)
 rng=random.Random(915190);samples=sorted(rng.sample(range(64),a.samples));records=[]
 for iteration in range(4):
  row,ops=solve(a.side,samples,a.stages,seconds=a.seconds,split=a.split,constant=not a.loose);records.append(row)
  if ops is not None:
   bad,words,codes=evaluate(ops,a.side,split=a.split,constant=not a.loose);row['bad_full_inputs']=len(bad)
   if not bad:
    q,report=verify(ops,words,codes);row['verification']=report;row['codes']=codes
    (a.outdir/'encoder.qasm').write_text(qasm2.dumps(q))
    from post190_joint_compose import compose
    from exhaustive_verify import exhaustive
    full,full_report=compose({a.side:q});oracle_path=a.outdir/'oracle.qasm'
    oracle_path.write_text(qasm2.dumps(full));exhaustive(oracle_path)
    row['full_oracle']=full_report
   else:samples=sorted(set(samples)|set(rng.sample(bad,min(12,len(bad)))))
  (a.outdir/'report.json').write_text(json.dumps(records,indent=2));print({k:v for k,v in row.items() if k not in ('ops','codes')},flush=True)
  if ops is None or not row.get('bad_full_inputs',0):break
