"""Search inexpensive linear recodings of the current three loaded code bits.
The exact inverse frame restores the existing kernel's labels; relative input
phases are canceled by using the actual inverse of the complete encoder.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from distributed_frame_search import FRAMES,native
from distributed_ucry import structured_ucry
from post218_bank_loader import bank_ucry
from post258_encoder_lifts import best_lift,H
from post258_two_stage_anf import decode
from post258_joint_encoder_schedule import touches
from build_two_stage_196 import KERNEL_WIRES
from exhaustive_verify import exhaustive
import two_stage_oracle as ts

def relative_body(raw):
 body=list(raw.data)[3:-3]
 while body and body[-1].operation.name=='cx':
  a,b=[raw.find_bit(w).index for w in body[-1].qubits]
  if a>=6 or b<6:break
  body.pop()
 q=QuantumCircuit(9);q.h([6,7,8])
 for inst in body:q.append(inst.operation,[raw.find_bit(w).index for w in inst.qubits])
 q.h([6,7,8]);return q

def run(outdir,seeds):
 assert not outdir.exists();outdir.mkdir(parents=True)
 codes=json.loads(Path('artifacts/196/class_codes.json').read_text());bags=[];report=[]
 for side,cls,mask,key in [(0,ts.ROWCLS,32,'ylab'),(1,ts.COLCLS,48,'xlab')]:
  lab=decode(codes[key]);values=[lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)]
  truth={m:np.array([(m&v).bit_count()%2 for v in values]) for m in range(1,8)}
  lifted={m:best_lift(t,196+side*8+m)[0] for m,t in truth.items()}
  raw_options=[]
  for frame in FRAMES:
   for variant,vecs in [('binary',truth),('lifted',lifted)]:
    tab=math.pi*np.array([vecs[m] for m in frame])
    for seed in range(seeds):
     raw=structured_ucry(tab,[6,7,8],list(range(6)),seed,sparse=True)
     q=relative_body(raw)
     for a,b in reversed(FRAMES[frame]):q.cx(6+a,6+b)
     if side:q.cx(5,4)
     raw_options.append((q.depth(),q.size(),frame,variant,seed,'structured',q))
  # Compile the promising raw schedules; add a separate sparse tour scheduler
  # for frames selected by spectral support, with no fixed 77-depth assumption.
  frames=sorted(FRAMES,key=lambda f:(sum(np.count_nonzero(H@lifted[m]) for m in f),len(FRAMES[f])))[:18]
  for frame in frames:
   tab=math.pi*np.array([lifted[m] for m in frame])
   for seed in range(seeds):
    q=relative_body(bank_ucry(tab,[6,7,8],list(range(6)),seed,tries=8))
    for a,b in reversed(FRAMES[frame]):q.cx(6+a,6+b)
    if side:q.cx(5,4)
    raw_options.append((q.depth(),q.size(),frame,'lifted',seed,'bank',q))
  unique={};best=999
  for _,_,frame,variant,seed,kind,raw in sorted(raw_options,key=lambda x:x[:2])[:100]:
   e=native(raw);times=tuple(touches(e));meta=dict(frame=frame,variant=variant,seed=seed,kind=kind,depth=e.depth(),cx=e.count_ops().get('cx',0),times=times)
   if e.depth()<best:best=e.depth();print('loader',side,meta,flush=True)
   if times not in unique or e.size()<unique[times][0].size():unique[times]=(e,meta)
  # Retain the protected construction too, so combinations can only improve.
  from post224_relative_lookup import relative
  tab=math.pi*np.array([truth[1<<b] for b in range(3)])
  e=relative(tab,99 if side==0 else 155)[0]
  if side:e.cx(5,4)
  unique[tuple(touches(e))]=(e,dict(kind='baseline',depth=e.depth(),times=touches(e)))
  bag=sorted(unique.values(),key=lambda v:(v[0].depth(),v[0].size()))[:24]
  for e,meta in bag:
   err=0.
   for v in range(64):
    s=Statevector.from_int(v,512).evolve(e).data
    w=(v^(((v>>5)&1)<<4) if side else v)|(values[v]<<6)
    assert abs(s[w])>.99
    want=np.zeros(512,complex);want[w]=s[w]/abs(s[w]);err=max(err,float(max(abs(s-want))))
   assert err<1e-10;meta['error']=err
  bags.append(bag);report.append([m for _,m in bag]);print('side complete',side,'options',len(raw_options),'best',best,flush=True)
  (outdir/'loaders.json').write_text(json.dumps(report,indent=2))
 kern=qasm2.load('artifacts/196/kernel.qasm');best=(196,858);rows=[]
 pairs=[]
 for ey,my in bags[0]:
  for ex,mx in bags[1]:
   before=list(mx['times'][:6])+list(my['times'][:6])+list(my['times'][6:])+list(mx['times'][6:]);after=before.copy()
   for w,t in zip(KERNEL_WIRES,touches(kern,[before[w] for w in KERNEL_WIRES])):after[w]=t
   pairs.append((max(a+b for a,b in zip(before,after)),ey,ex,my,mx))
 for _,ey,ex,my,mx in sorted(pairs,key=lambda v:v[0])[:100]:
  enc=QuantumCircuit(18);enc.compose(ey,ts.YW+ts.YA,inplace=True);enc.compose(ex,ts.XW+ts.XA,inplace=True)
  q=native(enc.compose(kern,KERNEL_WIRES).compose(enc.inverse()));score=(q.depth(),q.count_ops().get('cx',0))
  if score<best:
   path=outdir/f'oracle_d{score[0]}_cx{score[1]}.qasm';path.write_text(qasm2.dumps(q));exhaustive(path);best=score
   row=dict(depth=score[0],cx=score[1],y=my,x=mx,path=str(path));rows.append(row);print('improvement',row,flush=True)
 (outdir/'report.json').write_text(json.dumps(dict(seeds=seeds,rows=rows,best=best),indent=2))
 print('finished',best,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seeds',type=int,default=12);a=p.parse_args();run(a.outdir,a.seeds)
