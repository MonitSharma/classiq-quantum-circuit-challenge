"""Search quadratic coordinate changes whose controls are short linear parities."""
import json,math,itertools
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from distributed_ucry import rank,change_basis
from distributed_frame_search import native
from post258_kernel_schedule import synth

def run():
 out=Path('artifacts/post221_affine_toffoli_v2');assert not out.exists();out.mkdir();r=json.loads(Path('artifacts/221/class_codes.json').read_text());v=np.arange(256,dtype=np.uint16)
 truth=np.array([sum(m&~w==0 for m in r['terms'])%2 for w in v],np.uint8);moves=[];tables=[]
 for t in range(8):
  masks=[a for a in range(1,256) if not a>>t&1 and a.bit_count()<=2]
  for a,b in itertools.combinations(masks,2):
   for oa,ob in [(0,0),(0,1),(1,0),(1,1)]:
    flip=np.array([(((int(w)&a).bit_count()%2)^oa)&(((int(w)&b).bit_count()%2)^ob) for w in v],np.uint16)
    tables.append(truth[v^(flip<<t)]);moves.append((a,b,t,oa,ob))
 arr=np.array(tables);anf=arr.copy()
 for bit in range(8):
  for m in range(256):
   if m>>bit&1:anf[:,m]^=anf[:,m^(1<<bit)]
 costs=np.array([[0,.05,.5,1,4,12,30,80,200][m.bit_count()] for m in range(256)])
 rawscore=anf@costs;penalty=np.array([2*(a.bit_count()+b.bit_count()-2) for a,b,*_ in moves]);order=np.argsort(rawscore+penalty)
 chosen=[];seen=set()
 for i in order:
  key=bytes(anf[i])
  if key in seen:continue
  seen.add(key);chosen.append(int(i))
  if len(chosen)==20:break
 print('screen',len(moves),'best',float(rawscore[order[0]]),moves[order[0]],flush=True)
 best=(9999,9999);rows=[];want=np.diag((-1.)**truth)
 for idx in chosen:
  a,b,t,oa,ob=moves[idx];choices=[]
  for pa in range(8):
   for pb in range(8):
    if pa==pb or t in [pa,pb]:continue
    rowsbasis=[1<<j for j in range(8)];rowsbasis[pa]=a;rowsbasis[pb]=b
    if rank(rowsbasis)!=8:continue
    aff=change_basis(tuple(1<<j for j in range(8)),tuple(rowsbasis));choices.append((aff.depth(),aff.size(),pa,pb,aff))
  _,_,pa,pb,aff=min(choices,key=lambda v:v[:2]);g=aff.copy()
  if oa:g.x(pa)
  if ob:g.x(pb)
  g.rccx(pa,pb,t)
  if oa:g.x(pa)
  if ob:g.x(pb)
  g.compose(aff.inverse(),inplace=True);g=native(g)
  terms=np.flatnonzero(anf[idx]);angles=math.pi*np.array([sum(int(m)&~w==0 for m in terms) for w in range(256)])
  for seed in [0,3,11,21,28,91]:
   core=native(synth(angles,seed));q=native(g.compose(core).compose(g.inverse()));sc=(q.depth(),q.count_ops().get('cx',0))
   if sc<best:
    best=sc;p=out/f'kernel_d{sc[0]}_cx{sc[1]}.qasm';p.write_text(qasm2.dumps(q));op=Operator(qasm2.load(p)).data;overlap=np.vdot(want,op);err=float(np.max(abs(op-overlap/abs(overlap)*want)));assert err<1e-10
    row=dict(move=moves[idx],cost=float(rawscore[idx]),seed=seed,depth=sc[0],cx=sc[1],change_depth=g.depth(),core_depth=core.depth(),error=err,path=str(p));rows.append(row);print(row,flush=True)
 (out/'report.json').write_text(json.dumps(dict(screened=len(moves),rows=rows),indent=2)+'\n')
if __name__=='__main__':run()
