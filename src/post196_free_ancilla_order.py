"""Kernel restoration up to an ancilla permutation, with rewired uncompute.

Only the six clean ancillas may move. Coordinate wires remain fixed. This
changes the full unitary outside the required clean-ancilla input subspace.
"""
import argparse,json,random
from pathlib import Path
from qiskit import QuantumCircuit,qasm2
from distributed_frame_search import native
from build_two_stage_196 import encoders,KERNEL_WIRES
from post258_joint_encoder_schedule import touches
from exhaustive_verify import exhaustive

def prefix_of(kernel):
 last=max(i for i,inst in enumerate(kernel.data) if inst.operation.name!='cx')
 prefix=QuantumCircuit(8);prefix.global_phase=kernel.global_phase
 basis=[1<<i for i in range(8)]
 for inst in kernel.data[:last+1]:
  ws=[kernel.find_bit(w).index for w in inst.qubits]
  prefix.append(inst.operation,ws)
  if inst.operation.name=='cx':basis[ws[1]]^=basis[ws[0]]
 return prefix,basis

def finish(basis,start,rng,seed):
 rows=basis.copy();times=start.copy();ops=[];used=set()
 def cx(a,b):
  rows[b]^=rows[a];times[a]=times[b]=max(times[a],times[b])+1;ops.append((a,b))
 order=list(range(8));rng.shuffle(order)
 for col in order:
  available=[i for i in range(8) if i not in used and (i not in (0,4) or i==col)]
  choices=[i for i in available if rows[i]>>col&1]
  if col in (0,4):
   pivot=col
   if not rows[pivot]>>col&1:
    helpers=[i for i in range(8) if i not in used and rows[i]>>col&1]
    helper=min(helpers,key=lambda i:times[i]+rng.random()*5)
    cx(helper,pivot)
  elif choices:
   pivot=min(choices,key=lambda i:times[i]+(rows[i].bit_count()-1)*(seed%5)+rng.random()*8)
  else:
   pivot=rng.choice(available)
   helpers=[i for i in range(8) if i not in used and rows[i]>>col&1]
   cx(rng.choice(helpers),pivot)
  targets=[i for i in range(8) if i!=pivot and rows[i]>>col&1]
  targets.sort(key=lambda i:times[i]+rng.random()*(seed%7))
  for i in targets:cx(pivot,i)
  used.add(pivot)
 assert sorted(rows)==[1<<i for i in range(8)] and rows[0]==1 and rows[4]==16
 return ops,[r.bit_length()-1 for r in rows],times

def run(out,seeds,kernel_path=Path('artifacts/196/kernel.qasm')):
 assert not out.exists();out.mkdir(parents=True)
 kernel=qasm2.load(kernel_path);prefix,basis=prefix_of(kernel)
 enc=encoders(json.loads(Path('artifacts/196/class_codes.json').read_text()),99,155)
 incoming=touches(enc);initial=touches(prefix,[incoming[w] for w in KERNEL_WIRES])
 inv=enc.inverse();inv_ops=[[inv.find_bit(w).index for w in i.qubits] for i in inv.data]
 options={};rng=random.Random(914196)
 for seed in range(seeds):
  ops,perm,times=finish(basis,initial,rng,seed)
  mapping=list(range(18))
  for wire,col in enumerate(perm):mapping[KERNEL_WIRES[col]]=KERNEL_WIRES[wire]
  full=incoming.copy()
  for w,t in zip(KERNEL_WIRES,times):full[w]=t
  for ws in inv_ops:
   targets=[mapping[w] for w in ws];end=max(full[w] for w in targets)+1
   for w in targets:full[w]=end
  key=(max(full),len(ops),tuple(perm))
  if key not in options:options[key]=(ops,mapping,seed)
 print('screened',seeds,'best predicted',min(options),flush=True)
 best=(196,858);rows=[]
 for predicted,(ops,mapping,seed) in sorted(options.items())[:80]:
  k=prefix.copy()
  for a,b in ops:k.cx(a,b)
  q=native(enc.compose(k,KERNEL_WIRES).compose(inv,mapping));text=qasm2.dumps(q);q=qasm2.loads(text)
  score=(q.depth(),q.count_ops().get('cx',0))
  row=dict(depth=score[0],cx=score[1],seed=seed,suffix=ops,uncompute_mapping=mapping,predicted_depth=predicted[0]);rows.append(row)
  if score<best:
   path=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';path.write_text(text);exhaustive(path);best=score
   row['path']=str(path);print('improvement',score,flush=True)
 (out/'report.json').write_text(json.dumps(dict(best=best,seeds=seeds,kernel_path=str(kernel_path),rows=rows),indent=2))
 print('finished',best,'best sampled',min((r['depth'],r['cx']) for r in rows),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=20000);p.add_argument('--kernel',type=Path,default=Path('artifacts/196/kernel.qasm'));a=p.parse_args();run(a.outdir,a.seeds,a.kernel)
