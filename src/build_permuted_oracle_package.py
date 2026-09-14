"""Replay a packaged permuted kernel with recorded compute/uncompute loaders."""
import argparse,json,hashlib
from pathlib import Path
from qiskit import qasm2
from build_two_stage_196 import encoders,KERNEL_WIRES
from distributed_frame_search import native

def build(package,out):
 assert not out.exists();out.mkdir(parents=True)
 r=json.loads((package/'replay_recipe.json').read_text());codes=json.loads((package/'class_codes.json').read_text())
 e=encoders(codes,*r['forward']);f=encoders(codes,*r['inverse']);mapping=r['mapping']
 assert mapping[:12]==list(range(12)) and sorted(mapping[12:])==list(range(12,18))
 q=native(e.compose(qasm2.load(package/'kernel.qasm'),KERNEL_WIRES).compose(f.inverse(),mapping))
 text=qasm2.dumps(q);sha=hashlib.sha256(text.encode()).hexdigest();assert sha==r['sha256'],(sha,r['sha256'])
 p=out/f'oracle_d{q.depth()}_cx{q.count_ops().get("cx",0)}.qasm';p.write_text(text);print('replay',q.depth(),q.count_ops().get('cx',0),sha,flush=True)
 return p
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args();f=build(a.package,a.outdir)
 if a.verify:
  from exhaustive_verify import exhaustive
  exhaustive(f)
