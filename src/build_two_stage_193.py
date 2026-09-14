"""Deterministically rebuild the 193-depth oracle with permuted uncomputation."""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from qiskit import qasm2
from build_two_stage_196 import encoders,KERNEL_WIRES
from post218_beam_phase import psynth
from post196_free_ancilla_order import prefix_of
from distributed_frame_search import native

def build(outdir,recipe=Path('artifacts/193/kernel_recipe.json')):
 assert not outdir.exists();outdir.mkdir(parents=True)
 r=json.loads(recipe.read_text());co=np.array(r['co'],float)*math.pi
 k=native(psynth(8,{m:float(co[m]) for m in range(1,256) if abs(co[m])>1e-10},
                  global_phase=float(co[0]),**r['beam']))
 prefix,basis=prefix_of(k)
 for a,b in r['suffix']:
  prefix.cx(a,b);basis[b]^=basis[a]
 mapping=list(range(18))
 assert sorted(basis)==[1<<w for w in range(8)]
 for wire,b in enumerate(basis):mapping[KERNEL_WIRES[b.bit_length()-1]]=KERNEL_WIRES[wire]
 assert mapping==r['uncompute_mapping'] and mapping[:12]==list(range(12))
 enc=encoders(r['class_codes'],99,155)
 q=native(enc.compose(prefix,KERNEL_WIRES).compose(enc.inverse(),mapping))
 text=qasm2.dumps(q);sha=hashlib.sha256(text.encode()).hexdigest()
 assert sha==r['sha256'],(sha,r['sha256'])
 path=outdir/'two_stage_193.qasm';path.write_text(text)
 (outdir/'kernel.qasm').write_text(qasm2.dumps(prefix))
 (outdir/'manifest.json').write_text(json.dumps(dict(depth=q.depth(),cx=q.count_ops().get('cx',0),width=q.num_qubits,sha256=sha),indent=2))
 print('rebuild',q.depth(),q.count_ops().get('cx',0),sha,flush=True)
 return path

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--recipe',type=Path,default=Path('artifacts/193/kernel_recipe.json'));p.add_argument('--verify',action='store_true');a=p.parse_args()
 result=build(a.outdir,a.recipe)
 if a.verify:
  from exhaustive_verify import exhaustive
  exhaustive(result)
