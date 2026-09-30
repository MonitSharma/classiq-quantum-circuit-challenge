"""Compile and verify the code/kernel co-design shortlist."""
import json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from post258_two_stage_anf import decode
from post224_relative_lookup import relative
from post221_lifted_relative import sparse_relative
from distributed_frame_search import native
from post258_kernel_schedule import synth
import two_stage_oracle as ts

def run():
 out=Path('artifacts/post221_joint_cost_build_v1');assert not out.exists();out.mkdir();recs=json.loads(Path('artifacts/post221_joint_cost_v1/report.json').read_text())['rows'];rows=[];best=(9999,9999)
 for idx,r in enumerate(recs[:16]):
  es=[];settings=[]
  for side,cls,mask,key in [(0,ts.ROWCLS,32,'ylab'),(1,ts.COLCLS,48,'xlab')]:
   lab=decode(r[key]);codes=[lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)];table=math.pi*np.array([[c>>b&1 for c in codes] for b in range(3)]);options=[]
   for seed in range(24):
    for sparse in [False,True]:
     e=sparse_relative(table,seed) if sparse else relative(table,seed)[0]
     if side:e.cx(5,4)
     options.append((e.depth(),e.size(),seed,sparse,e))
   d,_,seed,sparse,e=min(options,key=lambda v:v[:2]);es.append(e);settings.append(dict(depth=d,seed=seed,sparse=sparse))
  angles=math.pi*np.array([sum(m&~w==0 for m in r['terms']) for w in range(256)]);kernels=[native(synth(angles,seed)) for seed in range(24)];k=min(kernels,key=lambda q:(q.depth(),q.size()))
  enc=QuantumCircuit(18);enc.compose(es[0],ts.YW+ts.YA,inplace=True);enc.compose(es[1],ts.XW+ts.XA,inplace=True);q=native(enc.compose(k,[11,12,13,14,4,15,16,17]).compose(enc.inverse()));sc=(q.depth(),q.count_ops().get('cx',0));row=dict(index=idx,depth=sc[0],cx=sc[1],encoders=settings,kernel_depth=k.depth());rows.append(row);print(row,flush=True)
  if sc<best:
   best=sc;p=out/f'joint_d{sc[0]}_cx{sc[1]}.qasm';p.write_text(qasm2.dumps(q));(out/f'kernel_d{sc[0]}.qasm').write_text(qasm2.dumps(k));(out/f'codes_d{sc[0]}.json').write_text(json.dumps(r,indent=2)+'\n');row['path']=str(p)
   from exhaustive_verify import exhaustive
   exhaustive(p)
  (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':run()
