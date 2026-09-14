"""Local exact CNOT/phase window resynthesis with fixed boundary matrices."""
import argparse,json,random,time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
from post218_beam_phase import psynth
from depth_parity_network import restore,_coords
from post258_joint_encoder_schedule import touches
from distributed_frame_search import native
from build_two_stage_196 import encoders,KERNEL_WIRES
from exhaustive_verify import exhaustive


def sliceq(q,a,b):
 r=QuantumCircuit(q.num_qubits)
 for inst in q.data[a:b]:r.append(inst.operation,[q.find_bit(w).index for w in inst.qubits])
 return r


def polynomial(q):
 basis=[1<<i for i in range(q.num_qubits)];targets={};phase=float(q.global_phase)
 for inst in q.data:
  w=[q.find_bit(w).index for w in inst.qubits]
  if inst.operation.name=='cx':basis[w[1]]^=basis[w[0]]
  else:
   assert inst.operation.name in ('u3','u') and abs(float(inst.operation.params[0]))<1e-9
   angle=sum(float(p) for p in inst.operation.params[1:]);phase+=angle/2
   targets[basis[w[0]]]=targets.get(basis[w[0]],0)-angle/2
 return {m:c for m,c in targets.items() if abs(c)>1e-10},basis,phase


def finish_to(q,basis,goal):
 relative=[sum(1<<i for i in _coords(b,goal,len(goal))) for b in basis]
 return q.compose(restore(relative,len(goal)))


def run(out,trials):
 assert not out.exists();out.mkdir(parents=True)
 package=Path('artifacts/190');kernel=qasm2.load(package/'kernel.qasm')
 codes=json.loads((package/'class_codes.json').read_text());enc=encoders(codes,298,506)
 mapping=json.loads((package/'replay_recipe.json').read_text())['mapping']
 def full(k):return native(enc.compose(k,KERNEL_WIRES).compose(enc.inverse(),mapping))
 bestq=full(kernel);best=(bestq.depth(),bestq.count_ops().get('cx',0));rows=[];rng=random.Random(914191);start=time.time()
 for trial in range(trials):
  length=rng.choice((12,18,24,32,40,50,64));a=rng.randrange(max(1,len(kernel.data)-length));b=min(a+length,len(kernel.data))
  prefix=sliceq(kernel,0,a);window=sliceq(kernel,a,b);suffix=sliceq(kernel,b,len(kernel.data))
  targets,goal,phase=polynomial(window)
  if not targets:continue
  initial=touches(prefix);tail=touches(suffix.reverse_ops())
  def finalize(q,basis):
   r=finish_to(q,basis,goal);times=touches(r,initial)
   return (max(t+s for t,s in zip(times,tail)),r.size()),r
  candidate=psynth(8,targets,global_phase=phase,seed=trial,beam=24,branch=10,alpha=6.,timew=1.2,horizon=1.5,fill=3,initial_times=initial,finalize=finalize)
  candidate=native(candidate)
  k=native(prefix.compose(candidate).compose(suffix));k.global_phase+=kernel.global_phase
  q=full(k);score=(q.depth(),q.count_ops().get('cx',0))
  row=dict(trial=trial,window=[a,b],depth=score[0],cx=score[1]);rows.append(row)
  if score<best:
   want=Operator(window).data;got=Operator(candidate).data;p=np.vdot(want,got);p/=abs(p);error=float(np.max(abs(got-p*want)));assert error<1e-9,error
   path=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';path.write_text(qasm2.dumps(q));exhaustive(path)
   (out/f'kernel_d{score[0]}_cx{score[1]}.qasm').write_text(qasm2.dumps(k));row.update(path=str(path),window_error=error)
   kernel=k;best=score;print('IMPROVEMENT',row,flush=True)
  if trial%20==0:print('trial',trial,'best',best,'last',score,'seconds',round(time.time()-start),flush=True)
  (out/'report.json').write_text(json.dumps(dict(best=best,completed=trial+1,rows=rows,mapping=mapping),indent=2))
 print('done',best,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--trials',type=int,default=240);a=p.parse_args();run(a.outdir,a.trials)
