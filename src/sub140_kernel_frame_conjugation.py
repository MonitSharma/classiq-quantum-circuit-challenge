"""Search exact shallow CNOT-frame conjugations of the 190 kernel.

For a frame F on the eight descriptor wires, the sequence F-D-F^-1 is exact
when D is synthesized for the transformed phase table.  The complete oracle
is then encoder-(F D F^-1)-encoder^-1.  This probes cancellations at the
encoder/kernel boundary without changing the Boolean oracle.
"""
import argparse,json,math,random
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from build_two_stage_196 import encoders,KERNEL_WIRES
from distributed_frame_search import native
from post218_beam_phase import psynth
from depth_parity_network import walsh

def map_frame(gates,z):
 bits=[(z>>i)&1 for i in range(8)]
 for a,b in gates: bits[b]^=bits[a]
 return sum(v<<i for i,v in enumerate(bits))

def run(outdir, trials, seed):
 outdir.mkdir(parents=True,exist_ok=True);rng=random.Random(seed)
 recipe=Path('artifacts/193_cx853/phase_search_recipe.json')
 co=np.asarray(json.loads(recipe.read_text())['co'],float)
 base=walsh(co)*math.pi
 codes=json.loads(Path('artifacts/190/class_codes.json').read_text());enc=encoders(codes,298,506)
 best=None;rows=[]
 for trial in range(trials):
  gates=[]
  for _ in range(rng.randint(1,8)):
   a,b=rng.sample(range(8),2);gates.append((a,b))
  transformed=np.array([base[map_frame(gates,z)] for z in range(256)])
  wc=walsh(transformed/math.pi);targets={m:float(wc[m]) for m in range(1,256) if abs(wc[m])>1e-10}
  k=native(psynth(8,targets,global_phase=float(wc[0]),seed=trial,beam=64,branch=14,alpha=5.0,timew=0.35,horizon=1.0,fill=2))
  frame=QuantumCircuit(18)
  for a,b in gates:frame.cx(KERNEL_WIRES[a],KERNEL_WIRES[b])
  fused=native(enc.compose(frame).compose(k).compose(frame.inverse()).compose(enc.inverse()))
  row={'trial':trial,'frame':gates,'frame_gates':len(gates),'kernel_depth':k.depth(),'full_depth':fused.depth(),'full_cx':fused.count_ops().get('cx',0),'terms':len(targets)};rows.append(row)
  if best is None or (row['full_depth'],row['full_cx'])<(best['full_depth'],best['full_cx']):
   best=row;print(row,flush=True);(outdir/'best.json').write_text(json.dumps(row,indent=2)+'\n')
 (outdir/'report.json').write_text(json.dumps({'best':best,'rows':rows},indent=2)+'\n');print('done',best,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--trials',type=int,default=30);p.add_argument('--seed',type=int,default=20260922);a=p.parse_args();run(a.outdir,a.trials,a.seed)
