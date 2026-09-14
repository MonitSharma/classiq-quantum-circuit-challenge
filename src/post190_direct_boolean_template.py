"""Bounded synthesis of a direct compute/Z/uncompute oracle, with no loaders.

Six disjoint relative-phase Toffolis per nonlinear stage, and matching CNOT
layers between stages. If synthesis succeeds for six stages and three CNOT
layers per gap, the constructive native depth ceiling is 139, using 18 wires.
A timeout is UNKNOWN, never an impossibility proof or a circuit result.
"""
import argparse,json,time,random,hashlib
from pathlib import Path
import numpy as np
import z3
from qiskit import QuantumCircuit,qasm2
from distributed_frame_search import native
from exhaustive_verify import exhaustive
from two_stage_oracle import logo

def selector(values,index):
 out=values[-1]
 for i in reversed(range(len(values)-1)):out=z3.If(index==i,values[i],out)
 return out

def assemble_oracle(ops):
 # Explicit native primitives retain the constructive schedule ceiling even
 # if an optional whole-circuit compiler pass chooses a deeper decomposition.
 primitive=QuantumCircuit(3);primitive.rccx(0,1,2);primitive=native(primitive)
 assert primitive.depth()<=9
 e=QuantumCircuit(18)
 for kind,w in ops:
  if kind=='cx':e.cx(*w)
  else:e.compose(primitive,w,inplace=True)
 q=e.copy();q.u(0,0,np.pi,17);q.compose(e.inverse(),inplace=True)
 # Qiskit's u gate and u3 have the same matrix; spell the basis explicitly.
 from qiskit.circuit.library import U3Gate
 explicit=QuantumCircuit(18);explicit.global_phase=q.global_phase
 for inst in q.data:
  wires=[q.find_bit(w).index for w in inst.qubits]
  explicit.append(U3Gate(*inst.operation.params) if inst.operation.name=='u' else inst.operation,wires)
 optimized=native(explicit)
 return min([explicit,optimized],key=lambda c:(c.depth(),c.count_ops().get('cx',0)))

def solve(samples,layers,gaps,seconds,target_function=logo,force_identity_tail=False):
 size=len(samples);solver=z3.Solver();solver.set(timeout=int(seconds*1000))
 state=[z3.BitVecVal(sum(((v>>w)&1)<<i for i,v in enumerate(samples)),size) for w in range(12)]+[z3.BitVecVal(0,size)]*6
 target=z3.BitVecVal(sum(int(target_function(v&63,v>>6))<<i for i,v in enumerate(samples)),size)
 definitions=[]
 def permutation(name,group):
  p=[z3.BitVec(f'{name}_{i}',5) for i in range(18)]
  for v in p:solver.add(z3.ULT(v,18))
  solver.add(z3.Distinct(p))
  for j in range(1,18//group):solver.add(z3.ULT(p[group*j+group-1],p[group*(j-1)+group-1])==False)
  if group==3:
   for j in range(6):solver.add(z3.ULT(p[3*j],p[3*j+1]))
  return p
 for layer in range(layers):
  if layer:
   for gap in range(gaps):
    p=permutation(f'cx_{layer}_{gap}',2);on=[z3.Bool(f'cx_on_{layer}_{gap}_{i}') for i in range(9)]
    old=state;controls=[selector(old,p[2*i]) for i in range(9)];state=[]
    for wire in range(18):
     value=old[wire]
     for i in range(9):value=z3.If(z3.And(on[i],p[2*i+1]==wire),old[wire]^controls[i],value)
     state.append(value)
    definitions.append(('cx',p,on))
  if layer==0:
   triples=[(2*i,2*i+1,12+i) for i in range(6)];old=state;state=old.copy()
   for a,b,t in triples:state[t]=old[t]^(old[a]&old[b])
   definitions.append(('fixed',triples,None))
  else:
   p=permutation(f'and_{layer}',3);on=[z3.Bool(f'and_on_{layer}_{i}') for i in range(6)];old=state
   products=[selector(old,p[3*i])&selector(old,p[3*i+1]) for i in range(6)];state=[]
   for wire in range(18):
    value=old[wire]
    for i in range(6):value=z3.If(z3.And(on[i],p[3*i+2]==wire),old[wire]^products[i],value)
    state.append(value)
   definitions.append(('and',p,on))
 if force_identity_tail:
  for _,_,on in definitions:
   if on is not None:solver.add([z3.Not(b) for b in on])
 solver.add(state[17]==target);start=time.time();status=solver.check();record=dict(status=str(status),seconds=time.time()-start,samples=len(samples))
 if status!=z3.sat:
  if status==z3.unknown:record['reason']=solver.reason_unknown()
  return record,None
 m=solver.model();ops=[]
 for kind,p,on in definitions:
  if kind=='fixed':ops.extend([('ccx',list(t)) for t in p]);continue
  order=[m.eval(v).as_long() for v in p];step=2 if kind=='cx' else 3
  for i,enabled in enumerate(on):
   if z3.is_true(m.eval(enabled,model_completion=True)):ops.append(('cx' if step==2 else 'ccx',order[step*i:step*(i+1)]))
 record['ops']=ops;return record,ops

def run(out,layers,gaps,seconds,rounds):
 assert not out.exists();out.mkdir(parents=True)
 rng=random.Random(190);samples=sorted({0,4095,*rng.sample(range(4096),14)});rows=[]
 for iteration in range(rounds):
  record,ops=solve(samples,layers,gaps,seconds);record['iteration']=iteration;rows.append(record)
  if ops is not None:
   words=np.arange(4096,dtype=np.int64)
   for kind,w in ops:
    if kind=='cx':a,b=w;words^=(words>>a&1)<<b
    else:a,b,t=w;words^=((words>>a&1)&(words>>b&1))<<t
   expected=np.array([int(logo(v&63,v>>6)) for v in range(4096)]);bad=np.flatnonzero((words>>17&1)!=expected).tolist();record['counterexamples']=len(bad)
   if not bad:
    q=assemble_oracle(ops)
    assert q.depth()<=2*(9*layers+gaps*(layers-1))+1
    f=out/f'direct_d{q.depth()}_cx{q.count_ops().get("cx",0)}.qasm';f.write_text(qasm2.dumps(q));exhaustive(f);record['qasm']=str(f)
   else:samples=sorted(set(samples)|set(rng.sample(bad,min(16,len(bad)))))
  (out/'report.json').write_text(json.dumps(dict(layers=layers,cnot_layers_per_gap=gaps,native_depth_ceiling=2*(9*layers+gaps*(layers-1))+1,rows=rows),indent=2))
  print({k:v for k,v in record.items() if k!='ops'},flush=True)
  if ops is None or not record.get('counterexamples',0):break
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--layers',type=int,default=6);p.add_argument('--gaps',type=int,default=3);p.add_argument('--seconds',type=float,default=30);p.add_argument('--rounds',type=int,default=4);a=p.parse_args();run(a.outdir,a.layers,a.gaps,a.seconds,a.rounds)
