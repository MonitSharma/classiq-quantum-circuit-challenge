"""Synthesize a reversible six-wire map into three raw class tags.

Each tag bucket may contain at most two classes, permitting a one-bit loader.
This is a different resource split from the four-output nine-wire encoders.
"""
import argparse,json,time
from functools import reduce
from pathlib import Path
import z3
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from distributed_ucry import rank,change_basis
from distributed_frame_search import native
import two_stage_oracle as ts

def xor(xs):return reduce(lambda a,b:a^b,xs)
def run(side,layers,timeout):
 out=Path(f'artifacts/post221_three_raw_{side}_l{layers}_v1');assert not out.exists();out.mkdir();cls=ts.ROWCLS if side=='y' else ts.COLCLS;s=z3.Solver();s.set(timeout=timeout);n=64;zero=z3.BitVecVal(0,n);ones=z3.BitVecVal((1<<n)-1,n)
 regs=[z3.BitVecVal(sum(((v>>b)&1)<<v for v in range(64)),n) for b in range(6)];matrices=[];offs=[];enabled=[]
 for stage in range(layers+1):
  count=3 if stage==layers else 6
  a=[[z3.Bool(f'a{stage}_{i}_{j}') for j in range(6)] for i in range(count)];off=[z3.Bool(f'o{stage}_{i}') for i in range(count)];matrices.append(a);offs.append(off)
  if stage<layers:
   inv=[[z3.Bool(f'inv{stage}_{i}_{j}') for j in range(6)] for i in range(6)]
   for i in range(6):
    for j in range(6):s.add(xor([z3.And(a[i][k],inv[k][j]) for k in range(6)])==(i==j))
  new=[z3.BitVec(f'r{stage}_{i}',n) for i in range(count)]
  for i in range(count):s.add(new[i]==xor([z3.If(a[i][j],regs[j],zero) for j in range(6)])^z3.If(off[i],ones,zero))
  regs=new
  if stage<layers:
   en=[z3.Bool(f'en{stage}_{i}') for i in range(2)];enabled.append(en);s.add(z3.Implies(en[1],en[0]))
   for g in range(2):regs[g*3+2]=regs[g*3+2]^z3.If(en[g],regs[g*3]&regs[g*3+1],zero)
 allowed=[[z3.Bool(f'allowed{tag}_{c}') for c in range(11)] for tag in range(8)]
 for row in allowed:s.add(z3.PbLe([(a,1) for a in row],2))
 tags=[z3.Concat(*[z3.Extract(v,v,regs[b]) for b in reversed(range(3))]) for v in range(64)];s.add(tags[0]==0)
 for v,c in enumerate(cls):
  for tag in range(8):s.add(z3.Implies(tags[v]==tag,allowed[tag][c]))
 start=time.monotonic();status=s.check();row=dict(side=side,layers=layers,status=str(status),seconds=time.monotonic()-start);print(row,flush=True)
 if status==z3.sat:
  model=s.model();val=lambda b:int(z3.is_true(model.eval(b,model_completion=True)));mats=[[[val(b) for b in rr] for rr in a] for a in matrices];offsets=[[val(b) for b in o] for o in offs];ens=[[val(b) for b in e] for e in enabled]
  last=[sum(b<<j for j,b in enumerate(rr)) for rr in mats[-1]];assert rank(last)==3
  for i in range(6):
   if rank(last+[1<<i])>len(last):last.append(1<<i)
  mats[-1]=[[v>>j&1 for j in range(6)] for v in last];offsets[-1]+=[0]*3
  q=QuantumCircuit(6)
  for st,(a,o) in enumerate(zip(mats,offsets)):
   basis=tuple(sum(b<<j for j,b in enumerate(rr)) for rr in a);q.compose(change_basis(tuple(1<<i for i in range(6)),basis),inplace=True)
   for i,b in enumerate(o):
    if b:q.x(i)
   if st<layers:
    for g,on in enumerate(ens[st]):
     if on:q.rccx(g*3,g*3+1,g*3+2)
  q=native(q);mapping=[]
  for v in range(64):
   state=Statevector.from_int(v,64).evolve(q).data;w=int(abs(state).argmax());assert abs(abs(state[w])-1)<1e-10;mapping.append(w)
  assert len(set(mapping))==64;groups=[set() for _ in range(8)]
  for v,w in enumerate(mapping):groups[w&7].add(cls[v])
  assert max(map(len,groups))<=2
  p=out/f'tags_d{q.depth()}.qasm';p.write_text(qasm2.dumps(q));row.update(matrices=mats,offsets=offsets,enabled=ens,mapping=mapping,groups=[sorted(g) for g in groups],depth=q.depth(),cx=q.count_ops().get('cx',0),path=str(p));print('verified tag map',q.depth(),flush=True)
 (out/'report.json').write_text(json.dumps(row,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--side',choices=['y','x'],required=True);p.add_argument('--layers',type=int,default=2);p.add_argument('--timeout-ms',type=int,default=55000);a=p.parse_args();run(a.side,a.layers,a.timeout_ms)
