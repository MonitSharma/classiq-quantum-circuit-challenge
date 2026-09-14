"""Native lowering of the general two-in-place/two-ancilla witnesses."""
import argparse,json,math,itertools
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.circuit.library import UCRYGate
from qiskit.synthesis.linear import synth_cnot_count_full_pmh
from distributed_ucry import coordinates,structured_ucry
from distributed_frame_search import native
from post224_clean_parity import synth_clean
from depth_parity_network import walsh
from post258_kernel_schedule import synth
import two_stage_oracle as ts

OPS=('x0','x1','c01','c10')
def perm_apply(p,op):
 q=list(p)
 for t in range(4):
  value=p[t];b=[value&1,(value>>1)&1]
  if op=='x0':b[0]^=1
  elif op=='x1':b[1]^=1
  elif op=='c01':b[1]^=b[0]
  else:b[0]^=b[1]
  q[t]=b[0]|(b[1]<<1)
 return tuple(q)
def decompose(p):
 start=tuple(range(4));front=[(start,())];seen={start}
 for _ in range(8):
  nxt=[]
  for cur,path in front:
   if cur==p:return path
   for op in OPS:
    z=perm_apply(cur,op)
    if z not in seen:seen.add(z);nxt.append((z,path+(op,)))
  front=nxt
 raise AssertionError(p)

def basis_change(basis):
 # Output i is the i-th coefficient of the input vector in ``basis``;
 # synth_cnot_count_full_pmh expects matrix rows as output parities.
 coeff=[coordinates(1<<j,basis) for j in range(6)]
 rows=[sum(((coeff[j]>>i)&1)<<j for j in range(6)) for i in range(6)]
 mat=np.array([[(r>>j)&1 for j in range(6)] for r in rows],dtype=bool)
 opts=[synth_cnot_count_full_pmh(mat,section_size=s) for s in (1,2,3)]
 return min(opts,key=lambda q:(q.depth(),q.size()))

def change_circuit(data, seed_base=0):
 basis=data['basis'];q=QuantumCircuit(9);q.compose(basis_change(basis),range(6),inplace=True)
 seq=[decompose(tuple(data['assign'][row])) for row in range(16)]
 for stage in range(max(map(len,seq))):
  # Group both unconditional flips in one three-output UCR and use the third
  # output as a zero-angle spectator.  Controlled CNOTs are similarly grouped
  # over the row bits and the other in-place bit.  q7/q8 are clean spectators;
  # zero-angle output rows leave them unchanged while allowing the six-control
  # interface of structured_ucry to be used.
  active={op:{row for row in range(16) if stage<len(seq[row]) and seq[row][stage]==op} for op in OPS}
  if active['x0'] or active['x1']:
   tab=np.zeros((3,64))
   for mask in range(64):
    row=mask&15
    tab[0,mask]=math.pi*int(row in active['x0'])
    tab[1,mask]=math.pi*int(row in active['x1'])
   q.compose(structured_ucry(tab,[0,1,6],[2,3,4,5,7,8],seed_base),inplace=True)
  if active['c01']:
   tab=np.zeros((3,64))
   for mask in range(64):tab[0,mask]=math.pi*int((mask&15) in active['c01'] and ((mask>>4)&1))
   q.compose(structured_ucry(tab,[1,6,7],[2,3,4,5,0,8],seed_base+1),inplace=True)
  if active['c10']:
   tab=np.zeros((3,64))
   for mask in range(64):tab[0,mask]=math.pi*int((mask&15) in active['c10'] and ((mask>>4)&1))
   q.compose(structured_ucry(tab,[0,6,7],[2,3,4,5,1,8],seed_base+2),inplace=True)
 return q

def side(data,side,cls,seed_base=0):
 q=change_circuit(data,seed_base);basis=data['basis'];mapping=[]
 for v in range(64):
  z=coordinates(v,basis);row=z>>2;t=z&3;zp=(z&~3)|data['assign'][row][t];value=0
  # The basis-change circuit puts the six coordinate wires into coefficient
  # coordinates.  Keep that representation here; the inverse restores the
  # original physical coordinate value after the phase operation.
  mapping.append(zp)
 assert len(set(mapping))==64
 cells={}
 for v,c in enumerate(cls):cells.setdefault((mapping[v]&3,c),[]).append(v)
 labels={};
 for block in range(4):
  for label,c in enumerate(sorted({c for b,c in cells if b==block})):
   labels[(block,c)]=label
 table=np.zeros((3,64))
 for z,v in enumerate([next(i for i,m in enumerate(mapping) if m==z) for z in range(64)]):
  lab=labels[(z&3,cls[v])]
  for b in range(2):table[b,z]=math.pi*((lab>>b)&1)
 # Two outputs plus one explicitly clean helper fit exactly in this local
 # nine-wire block.  The helper is included in the parity synthesis domain,
 # so it is restored rather than assumed initialized by transpilation.
 phases=np.array([-.5*sum(table[b,w&(63)]*(-1)**(w>>(6+b)&1) for b in range(2)) for w in range(1<<8)])
 best=min((native(QuantumCircuit(9)) for _ in [0]),key=lambda x:x.depth())
 # Build the clean parity circuit directly, keeping the same two-output
 # layout as the table and q8 as its sole scratch wire.
 helper=QuantumCircuit(9)
 for b in (6,7):helper.rx(math.pi/2,b)
 helper.compose(synth_clean(phases,1,seed_base+3),inplace=True)
 for b in (6,7):helper.rx(-math.pi/2,b)
 e=q.compose(helper)
 return native(e),mapping,labels

def run(outdir,seeds):
 outdir.mkdir(parents=True,exist_ok=True);raw=json.loads(Path('artifacts/sub140_k2m2_v1.json').read_text())
 for key in ('x','y'):
  basis=list(raw[key]['gen'])
  for v in (1,2,4,8,16,32):
   if __import__('distributed_ucry').rank(basis+[v])>len(basis): basis.append(v)
   if len(basis)==6: break
  assert len(basis)==6
  raw[key]['basis']=basis
 by=raw['y']['basis'];bx=raw['x']['basis']
 ey,my,ly=side(raw['y'],'y',ts.ROWCLS);ex,mx,lx=side(raw['x'],'x',ts.COLCLS)
 print('encoders',ey.depth(),ey.count_ops().get('cx',0),ex.depth(),ex.count_ops().get('cx',0),flush=True)
 truth=np.zeros(256,int)
 for y in range(64):
  for x in range(64):
   yb=my[y]&3; xb=mx[x]&3
   truth[yb|((ly[(yb,ts.ROWCLS[y])])<<2)|(xb<<4)|((lx[(xb,ts.COLCLS[x])])<<6)]=ts.logo(x,y)
 k=min((native(synth(math.pi*truth,s)) for s in range(seeds)),key=lambda q:(q.depth(),q.size()))
 # Repository convention: x occupies q0..q5 and y occupies q6..q11.
 enc=QuantumCircuit(18);enc.compose(ex,list(range(6))+[12,13,14],inplace=True);enc.compose(ey,list(range(6,12))+[15,16,17],inplace=True)
 q=native(enc.compose(k,[6,7,15,16,0,1,12,13]).compose(enc.inverse()))
 p=outdir/f'k2m2_d{q.depth()}_cx{q.count_ops().get("cx",0)}.qasm';p.write_text(qasm2.dumps(q));print('full',q.depth(),q.count_ops().get('cx',0),p,flush=True)
 from exhaustive_verify import exhaustive;exhaustive(p)
 (outdir/'report.json').write_text(json.dumps({'depth':q.depth(),'cx':q.count_ops().get('cx',0),'encoders':[ey.depth(),ex.depth()],'path':str(p)},indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=8);a=p.parse_args();run(a.outdir,a.seeds)
