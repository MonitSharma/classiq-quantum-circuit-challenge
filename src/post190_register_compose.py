"""Verify and compose nine-wire replacements with the protected phase kernel."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from build_two_stage_196 import encoders,KERNEL_WIRES
from post190_degree_rank_bound import targets
from distributed_frame_search import native
from exhaustive_verify import exhaustive

WIRES={'y':[6,7,8,9,10,11,12,13,14],'x':[0,1,2,3,4,5,15,16,17]}

def validate_encoder(q,side):
 assert q.num_qubits==9 and set(q.count_ops())<={'u3','cx'}
 mask,raw=(32,5) if side=='y' else (48,4);t=targets()[side]
 for x in range(64):
  v=Statevector.from_int(x,512).evolve(q).data;dest=int(np.argmax(abs(v)))
  assert abs(abs(v[dest])-1)<1e-10,'encoder is not a basis permutation on care states'
  assert [(dest>>(6+b))&1 for b in range(3)]==[f[x] for f in t],'incorrect code'
  assert ((dest>>raw)&1)==(x&mask).bit_count()%2,'incorrect raw tag'


def compose(replacements):
 p=Path('artifacts/190');codes=json.loads((p/'class_codes.json').read_text());base=encoders(codes,298,506)
 for side,q in replacements.items():validate_encoder(q,side)
 if not replacements:e=base
 else:
  e=QuantumCircuit(18)
  for side,ws in WIRES.items():
   if side in replacements:e.compose(replacements[side],ws,inplace=True)
   else:
    for inst in base.data:
     physical=[base.find_bit(v).index for v in inst.qubits]
     if set(physical)<=set(ws):e.append(inst.operation,physical)
 k=qasm2.load(p/'kernel.qasm');mapping=json.loads((p/'replay_recipe.json').read_text())['mapping']
 return native(e.compose(k,KERNEL_WIRES).compose(e.inverse(),mapping))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--x',type=Path);p.add_argument('--y',type=Path);p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();assert not a.outdir.exists();a.outdir.mkdir(parents=True)
 replacements={s:qasm2.load(v) for s,v in [('x',a.x),('y',a.y)] if v}
 q=compose(replacements);text=qasm2.dumps(q);path=a.outdir/'oracle.qasm';path.write_text(text);exhaustive(path)
 r=dict(depth=q.depth(),cx=q.count_ops().get('cx',0),width=q.num_qubits,sha256=hashlib.sha256(text.encode()).hexdigest(),replacements={s:str(v) for s,v in [('x',a.x),('y',a.y)] if v},beats_protected=(q.depth(),q.count_ops().get('cx',0))<(190,857))
 (a.outdir/'report.json').write_text(json.dumps(r,indent=2));print(r)
