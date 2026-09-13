"""Audit guarded phase-loader schedules on all 64 promised inputs per side."""
import sys,json,math,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'src'))
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from distributed_ucry import walsh
from distributed_frame_search import native
from post218_beam_phase import psynth
from post258_two_stage_anf import decode
import two_stage_oracle as ts
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--outdir',type=Path,required=True);args=parser.parse_args()
out=args.outdir;assert not out.exists();out.mkdir(parents=True)
codes=json.loads(Path('artifacts/196/class_codes.json').read_text());rows=[]
for side,cls,mask,key in [(0,ts.ROWCLS,32,'ylab'),(1,ts.COLCLS,48,'xlab')]:
 lab=decode(codes[key]);values=[lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)]
 co=walsh(np.array([[math.pi*(c>>b&1) for c in values] for b in range(3)]))
 targets={m|(1<<(6+b)):-float(co[b,m])/2 for b in range(3) for m in range(64) if abs(co[b,m])>1e-12}
 for seed in range(3):
  start=time.time();body=psynth(9,targets,seed=seed,beam=12,branch=6,guard=448)
  q=QuantumCircuit(9);q.h([6,7,8]);q.compose(body,inplace=True);q.h([6,7,8]);q=native(q)
  err=0.
  for v in range(64):
   s=Statevector.from_int(v,512).evolve(q).data;w=v|(values[v]<<6);assert abs(s[w])>.99;want=np.zeros(512,complex);want[w]=s[w]/abs(s[w]);err=max(err,float(max(abs(s-want))))
  assert err<1e-10
  row=dict(side=side,seed=seed,body_depth=body.depth(),depth=q.depth(),cx=q.count_ops().get('cx',0),error=err,seconds=time.time()-start);rows.append(row);print(row,flush=True)
  (out/f'guard_side{side}_seed{seed}.qasm').write_text(qasm2.dumps(q));(out/'guard_report.json').write_text(json.dumps(rows,indent=2))
