"""Bounded nine-wire reversible synthesis with explicit register contents.

Only wires 6:9 start clean. Four outputs (a retained raw tag plus three code
bits) are prescribed; other coordinate wires may contain garbage. Every
operation is a reversible X, CX or relative-phase Toffoli. This directly
models dirty register reuse, unlike a logical XAG plus retirement flags.
"""
import argparse,json,time,random
from pathlib import Path
import numpy as np
import z3
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from distributed_frame_search import native
from post190_degree_rank_bound import targets


def select(values,index):
 out=values[-1]
 for i in reversed(range(len(values)-1)):out=z3.If(index==i,values[i],out)
 return out


def solve(side,samples,stages=4,cx_layers=2,seconds=15,synthetic=False):
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
 tables=targets()[side]
 rawmask,rawwire=(32,5) if side=='y' else (48,4)
 if synthetic:
  tables=[[(v>>(2*b)&1)&(v>>(2*b+1)&1) for v in range(64)] for b in range(3)]
 for w,t in [(6+b,t) for b,t in enumerate(tables)]+[(rawwire,[(v&rawmask).bit_count()%2 for v in range(64)])]:
  s.add(state[w]==z3.BitVecVal(sum(t[v]<<i for i,v in enumerate(samples)),size))
 start=time.time();status=s.check();row=dict(side=side,status=str(status),seconds=time.time()-start,samples=len(samples),stages=stages,cx_layers=cx_layers,depth_ceiling=2+9*stages+(stages+1)*cx_layers)
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


def build(ops):
 primitive=QuantumCircuit(3);primitive.rccx(0,1,2);primitive=native(primitive)
 q=QuantumCircuit(9)
 for kind,ws in ops:
  if kind=='ccx':q.compose(primitive,ws,inplace=True)
  elif kind=='cx':q.cx(*ws)
  else:q.x(ws[0])
 # Preserve the explicit native schedule as a fallback if transpilation deepens it.
 explicit=QuantumCircuit(9);explicit.global_phase=q.global_phase
 from qiskit.circuit.library import U3Gate
 for inst in q.data:
  ws=[q.find_bit(w).index for w in inst.qubits]
  explicit.append(U3Gate(np.pi,0,np.pi) if inst.operation.name=='x' else inst.operation,ws)
 return min([explicit,native(explicit)],key=lambda c:(c.depth(),c.size()))


def check(ops,side,synthetic=False):
 words=np.arange(64,dtype=int)
 for kind,ws in ops:
  if kind=='x':words^=1<<ws[0]
  elif kind=='cx':words^=((words>>ws[0])&1)<<ws[1]
  else:words^=(((words>>ws[0])&1)&((words>>ws[1])&1))<<ws[2]
 tables=targets()[side]
 if synthetic:tables=[[(v>>(2*b)&1)&(v>>(2*b+1)&1) for v in range(64)] for b in range(3)]
 mask,raw=(32,5) if side=='y' else (48,4)
 bad=[]
 for v in range(64):
  if any(((words[v]>>(6+b))&1)!=tables[b][v] for b in range(3)) or ((words[v]>>raw)&1)!=(v&mask).bit_count()%2:bad.append(v)
 return bad,words,tables


def verify(ops,side,synthetic=False):
 bad,words,tables=check(ops,side,synthetic);assert not bad
 q=build(ops);full=q.copy()
 for w in range(6,9):full.z(w)
 full.compose(q.inverse(),inplace=True);full=native(full);phase=None;err=0.
 for v in range(64):
  state=Statevector.from_int(v,512);out=state.evolve(q).data
  assert abs(abs(out[words[v]])-1)<1e-10
  result=state.evolve(full).data;sign=(-1)**sum(t[v] for t in tables)
  if phase is None:phase=result[v]/sign
  want=np.zeros(512,complex);want[v]=phase*sign;err=max(err,float(np.max(abs(result-want))))
 assert err<1e-10
 return q,dict(depth=q.depth(),cx=q.count_ops().get('cx',0),width=9,basis_inputs_checked=64,max_error=err,phase_oracle_depth=full.depth())

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seconds',type=float,default=15);p.add_argument('--samples',type=int,default=64);p.add_argument('--stages',type=int,default=4);p.add_argument('--synthetic',action='store_true');a=p.parse_args()
 assert not a.outdir.exists();a.outdir.mkdir(parents=True);rng=random.Random(190);samples=sorted(rng.sample(range(64),a.samples));rows=[]
 for it in range(4):
  row,ops=solve(a.side,samples,stages=a.stages,seconds=a.seconds,synthetic=a.synthetic);rows.append(row)
  if ops is not None:
   bad,_,_=check(ops,a.side,a.synthetic);row['bad_full_inputs']=len(bad)
   if not bad:
    q,report=verify(ops,a.side,a.synthetic);row['verification']=report;assert q.depth()<=row['depth_ceiling'];(a.outdir/'encoder.qasm').write_text(qasm2.dumps(q))
    if not a.synthetic:
     from post190_register_compose import compose
     from exhaustive_verify import exhaustive
     full=compose({a.side:q});path=a.outdir/'oracle.qasm';path.write_text(qasm2.dumps(full));exhaustive(path)
     row['full_oracle']={'depth':full.depth(),'cx':full.count_ops().get('cx',0),'path':str(path)}
   else:samples=sorted(set(samples)|set(rng.sample(bad,min(8,len(bad)))))
  (a.outdir/'report.json').write_text(json.dumps(rows,indent=2));print({k:v for k,v in row.items() if k!='ops'},flush=True)
  if ops is None or not row.get('bad_full_inputs',0):break
