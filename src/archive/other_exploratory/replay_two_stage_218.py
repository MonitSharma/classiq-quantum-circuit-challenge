"""Deterministic rebuild of the verified 218-depth oracle into a fresh directory."""
import argparse,json,math,hashlib
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from post224_relative_lookup import relative
from post258_two_stage_anf import decode
from post258_kernel_schedule import synth
from depth_parity_network import walsh
from distributed_frame_search import native
import two_stage_oracle as ts

def replay(outdir):
 assert not outdir.exists();outdir.mkdir(parents=True);base=Path('artifacts/218');r=json.loads((base/'class_codes.json').read_text());recipe=json.loads((base/'kernel_recipe.json').read_text());manifest=json.loads((base/'manifest.json').read_text())
 phases=walsh(np.array(recipe['co'],float)/32)*256*math.pi;k=native(synth(phases,recipe['seed']));ks=qasm2.dumps(k);assert hashlib.sha256(ks.encode()).hexdigest()==manifest['kernel_sha256'];(outdir/'kernel.qasm').write_text(ks)
 enc=QuantumCircuit(18)
 for side,cls,mask,key,seed,wires in [(0,ts.ROWCLS,32,'ylab',11,ts.YW+ts.YA),(1,ts.COLCLS,48,'xlab',151,ts.XW+ts.XA)]:
  lab=decode(r[key]);codes=[lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)];table=np.array([[math.pi*(c>>b&1) for c in codes] for b in range(3)]);e,_=relative(table,seed)
  if side:e.cx(5,4)
  enc.compose(e,wires,inplace=True)
 q=native(enc.compose(k,[11,12,13,14,4,15,16,17]).compose(enc.inverse()));text=qasm2.dumps(q);sha=hashlib.sha256(text.encode()).hexdigest();assert sha==manifest['sha256'];path=outdir/'two_stage_218.qasm';path.write_text(text)
 from exhaustive_verify import exhaustive
 exhaustive(path);print('Exact kernel and oracle replay:',sha,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);replay(p.parse_args().outdir)
