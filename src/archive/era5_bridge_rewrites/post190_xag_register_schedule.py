"""Exact finite search within a restricted affine-register XAG lowering model.

Six original inputs stay intact. Three ancillas contain XORs of named AND
signals. Free ancilla basis changes are allowed; a node may toggle a target
only when both operands can be obtained without that target. BFS minimizes
node toggles, not native depth. Exhaustion closes only this lowering model.
"""
import itertools,json,argparse
from collections import deque
from pathlib import Path
from qiskit import QuantumCircuit
from distributed_frame_search import FRAMES,native
from xag import linear_best
from post190_xag_inplace_lower import outputs
from qiskit.quantum_info import Statevector
import numpy as np


def basis(rows):
 piv={}
 for v in rows:
  for p in sorted(piv,reverse=True):
   if v>>p&1:v^=piv[p]
  if v:
   p=v.bit_length()-1
   for j in list(piv):
    if piv[j]>>p&1:piv[j]^=v
   piv[p]=v
 return tuple(piv[p] for p in sorted(piv,reverse=True))


def span(rows):
 out=[0]
 for r in rows:out += [v^r for v in out.copy()]
 return sorted(set(out))


def nodepart(form):return sum(1<<(i-6) for i in form[0] if i>=6)


def search(w,max_states=50000):
 assert w['k']==len(w['gates']) and len(w['outs'])==3
 for j,g in enumerate(w['gates']):
  for f in (g['a'],g['b']):
   assert len(set(f[0]))==len(f[0]) and all(0<=i<6+j for i in f[0])
 for f in w['outs']:
  assert len(set(f[0]))==len(f[0]) and all(0<=i<6+w['k'] for i in f[0])
 parents=[(nodepart(g['a']),nodepart(g['b'])) for g in w['gates']]
 goal=basis([nodepart(f) for f in w['outs']]);queue=deque([()]);prev={():None}
 while queue:
  state=queue.popleft()
  if state==goal:
   path=[]
   while prev[state] is not None:
    old,edge=prev[state];path.append(edge);state=old
   return dict(status='found',states=len(prev),toggles=len(path),path=path[::-1])
  vs=span(state);spaces={basis([a,b]) for a in vs for b in vs}
  for h in sorted(spaces):
   hs=set(span(h))
   v=next((v for v in vs if basis([*h,v])==state),None)
   if v is None:continue
   frame=tuple([*h,*([0]*(2-len(h))),v])
   for j,(a,b) in enumerate(parents):
    if a not in hs or b not in hs:continue
    new=basis([*h,v^(1<<j)])
    if new==state or new in prev:continue
    edge=dict(node=j,before=list(state),frame=list(frame),after=list(new))
    prev[new]=(state,edge);queue.append(new)
    if len(prev)>max_states:return dict(status='state_limit',states=len(prev))
 return dict(status='exhausted_restricted_model',states=len(prev))


def frame_ops(current,wanted):
 candidates=[]
 for matrix,ops in FRAMES.items():
  got=[]
  for row in matrix:
   v=0
   for i in range(3):
    if row>>i&1:v^=current[i]
   got.append(v)
  if got==list(wanted):candidates.append(ops)
 assert candidates,(current,wanted)
 return min(candidates,key=len)


def lower(w,plan):
 assert plan['status']=='found';q=QuantumCircuit(9);current=[0]*3
 def change(wanted):
  nonlocal current
  for a,b in frame_ops(current,wanted):q.cx(6+a,6+b)
  current=list(wanted)
 def app(pre):
  for inst in pre.data:q.append(inst.operation,[pre.find_bit(v).index for v in inst.qubits])
 for step in plan['path']:
  change(step['frame']);g=w['gates'][step['node']];forms=[]
  for f in [g['a'],g['b']]:
   wanted=nodepart(f);selection=next(i for i in range(4) if ((current[0] if i&1 else 0)^(current[1] if i&2 else 0))==wanted)
   form={s for s in f[0] if s<6}|{6+i for i in range(2) if selection>>i&1}
   if f[1]:form.add(-1)
   forms.append(frozenset(form))
  a,b=forms;linear=None
  if not a or not b or a==b^{-1}:pass
  elif a==b:linear=a
  elif a==frozenset([-1]):linear=b
  elif b==frozenset([-1]):linear=a
  else:
   pre,p,r=linear_best(None,a,b,{i:i for i in range(9)})
   app(pre);q.rccx(p,r,8);app(pre.inverse())
  if linear is not None:
   for v in sorted(linear):
    if v==-1:q.x(8)
    else:q.cx(v,8)
  current[2]^=1<<step['node']
  # Keep the physical frame until the next operation. Returning to canonical
  # form after every toggle introduces needless linear basis changes.
  assert basis(current)==tuple(step['after'])
 desired=[nodepart(f) for f in w['outs']]
 assert len(desired)==3
 change(desired)
 for j,(ss,c) in enumerate(w['outs']):
  if c:q.x(6+j)
  for v in ss:
   if v<6:q.cx(v,6+j)
 return native(q)


def verify(w,q):
 error=0.;full=q.copy()
 for i in range(6,9):full.z(i)
 full.compose(q.inverse(),inplace=True);full=native(full);phase=None
 for x in range(64):
  s=Statevector.from_int(x,512);v=s.evolve(q).data;t=outputs(w,x);dest=x+sum(b<<(6+i) for i,b in enumerate(t))
  assert abs(abs(v[dest])-1)<1e-10
  v=s.evolve(full).data;sign=(-1)**sum(t)
  if phase is None:phase=v[x]/sign
  want=np.zeros(512,complex);want[x]=phase*sign;error=max(error,float(np.max(abs(v-want))))
 assert error<1e-10
 return dict(depth=q.depth(),cx=q.count_ops().get('cx',0),width=9,max_error=error,basis_inputs_checked=64,phase_oracle_depth=full.depth())

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--witness',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--side',choices=['x','y']);a=p.parse_args();assert not a.outdir.exists();a.outdir.mkdir(parents=True)
 w=json.loads(a.witness.read_text())
 if a.side:
  from post190_degree_rank_bound import targets
  tables=targets()[a.side]
  assert all(outputs(w,x)==[t[x] for t in tables] for x in range(64)), 'witness does not match protected labels'
 r=search(w)
 if r['status']=='found':
  from qiskit import qasm2
  q=lower(w,r);r['verification']=verify(w,q);(a.outdir/'encoder.qasm').write_text(qasm2.dumps(q))
  if a.side:
   # This scheduler preserves all primary inputs. Expose x4 XOR x5 for
   # the kernel; y's raw tag is already its unchanged input bit 5.
   if a.side=='x':q.cx(5,4);q=native(q)
   (a.outdir/'encoder.qasm').write_text(qasm2.dumps(q))
   from post190_register_compose import compose
   from exhaustive_verify import exhaustive
   full=compose({a.side:q});path=a.outdir/'oracle.qasm';path.write_text(qasm2.dumps(full));exhaustive(path)
   r['full_oracle']={'depth':full.depth(),'cx':full.count_ops().get('cx',0),'path':str(path)}
 (a.outdir/'report.json').write_text(json.dumps(r,indent=2));print({k:v for k,v in r.items() if k!='path'},flush=True)
