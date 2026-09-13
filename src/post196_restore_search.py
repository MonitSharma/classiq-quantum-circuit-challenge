"""Optimize a kernel's final linear restoration using incoming wire times."""
import argparse,json,random
from pathlib import Path
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from distributed_frame_search import native
from build_two_stage_196 import encoders,KERNEL_WIRES
from post258_joint_encoder_schedule import touches
from exhaustive_verify import exhaustive

def run(outdir,seeds):
 assert not outdir.exists();outdir.mkdir(parents=True)
 kernel=qasm2.load('artifacts/196/kernel.qasm');last=max(i for i,inst in enumerate(kernel.data) if inst.operation.name!='cx')
 prefix=QuantumCircuit(8)
 for inst in kernel.data[:last+1]:prefix.append(inst.operation,[kernel.find_bit(w).index for w in inst.qubits])
 basis=[1<<i for i in range(8)]
 for inst in prefix.data:
  if inst.operation.name=='cx':a,b=[prefix.find_bit(w).index for w in inst.qubits];basis[b]^=basis[a]
 codes=json.loads(Path('artifacts/196/class_codes.json').read_text());enc=encoders(codes,99,155)
 options={};rng=random.Random(196);start=touches(prefix)
 for seed in range(seeds):
  rows=basis.copy();times=start.copy();ops=[]
  def cx(a,b):
   rows[b]^=rows[a];times[a]=times[b]=max(times[a],times[b])+1;ops.append((a,b))
  order=list(range(8));rng.shuffle(order)
  completed=set()
  for col in order:
   if not rows[col]>>col&1:
    choices=[i for i in range(8) if rows[i]>>col&1 and i!=col and i not in completed]
    pivot=rng.choice(choices);cx(pivot,col)
   targets=[i for i in range(8) if i!=col and rows[i]>>col&1]
   if seed%3==0:targets.sort(key=lambda i:times[i])
   else:rng.shuffle(targets)
   for i in targets:cx(col,i)
   completed.add(col)
  assert rows==[1<<i for i in range(8)]
  score=(max(times),len(ops))
  if score not in options:options[score]=(ops,seed)
 best=(196,858);records=[]
 for score,(ops,seed) in sorted(options.items())[:40]:
  k=prefix.copy()
  for a,b in ops:k.cx(a,b)
  k=native(k)
  assert Operator(kernel).equiv(Operator(qasm2.loads(qasm2.dumps(k))))
  q=native(enc.compose(k,KERNEL_WIRES).compose(enc.inverse()));sc=(q.depth(),q.count_ops().get('cx',0))
  rec=dict(seed=seed,kernel_depth=k.depth(),kernel_cx=k.count_ops().get('cx',0),depth=sc[0],cx=sc[1]);records.append(rec)
  if sc<best:
   path=outdir/f'oracle_d{sc[0]}_cx{sc[1]}.qasm';path.write_text(qasm2.dumps(q));exhaustive(path);rec['path']=str(path);best=sc;print('improved',rec,flush=True)
 (outdir/'report.json').write_text(json.dumps(dict(seeds=seeds,original_suffix=len(kernel.data)-last-1,best=best,rows=records),indent=2));print('restore finished',best,'old suffix',len(kernel.data)-last-1,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=10000);a=p.parse_args();run(a.outdir,a.seeds)
