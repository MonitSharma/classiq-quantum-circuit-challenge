"""Phase-equivalent cube additions, including monomials absent from the ANF."""
import argparse,json,math
from pathlib import Path
import numpy as np
from qiskit import qasm2
from qiskit.quantum_info import Operator
from depth_parity_network import walsh
from post258_kernel_schedule import synth
from distributed_frame_search import native

def run(outdir,steps,seeds):
 assert not outdir.exists();outdir.mkdir(parents=True);r=json.loads(Path('artifacts/221/class_codes.json').read_text());truth=np.array([sum(m&~w==0 for m in r['terms']) for w in range(256)])
 start=np.rint(32*walsh(truth)).astype(int)%32;start[0]=0
 masks=[m for m in range(1,256) if m.bit_count()<=6]
 moves=np.array([64*walsh([int(m&~w==0) for w in range(256)]) for m in masks]);assert np.max(abs(moves-moves.round()))<1e-9;moves=moves.round().astype(int);moves[:,0]=0
 moves=np.unique(np.concatenate([moves,-moves,2*moves,-2*moves,4*moves,8*moves])%32,axis=0)
 # Larger-angle rotations still count as one native gate; prioritize parity
 # support and congestion while preserving the exact modular phase vector.
 incidence=np.array([[m>>b&1 for b in range(8)] for m in range(256)],int)
 def score(a):
  nz=a!=0;return nz.sum(axis=-1)+.12*(nz@incidence).max(axis=-1)
 rng=np.random.default_rng(812);cur=start.copy();best=float(score(cur));candidates={};history=[]
 for step in range(steps):
  if step%500==0:
   cur=start.copy() if not candidates or rng.random()<.2 else np.array(rng.choice(list(candidates.values()))['co'],int)
   for _ in range(3):cur=(cur+moves[int(rng.integers(len(moves)))])%32
  nxt=(cur[None,:]+moves)%32;vals=score(nxt);ids=np.flatnonzero(vals==vals.min());idx=int(rng.choice(ids));temp=.05+2*(1-step%500/500)
  if vals[idx]<=score(cur) or rng.random()<math.exp(min(0,(score(cur)-vals[idx])/temp)):cur=nxt[idx]
  value=float(score(cur));key=tuple(cur)
  if value<=best+1 and key not in candidates:
   # Modular exact check: every input gets the same global phase change.
   diff=np.rint(walsh((cur-start).astype(float))*256).astype(int);assert np.all((diff-diff[0])%64==0)
   candidates[key]=dict(step=step,cost=value,support=int(np.count_nonzero(cur)),co=cur.tolist())
  if value<best:best=value;history.append(candidates[key]);print('phase',step,best,np.count_nonzero(cur),flush=True)
 selected=sorted(candidates.values(),key=lambda r:r['cost'])[:12];nativebest=(9999,9999);rows=[]
 for row in selected:
  phases=walsh(np.array(row['co'],float)/32)*256*math.pi
  for seed in range(seeds):
   k=native(synth(phases,seed));sc=(k.depth(),k.count_ops().get('cx',0))
   if sc<nativebest:
    nativebest=sc;p=outdir/f'kernel_d{sc[0]}_cx{sc[1]}.qasm';p.write_text(qasm2.dumps(k));op=Operator(qasm2.load(p)).data;want=np.diag(np.exp(1j*math.pi*truth));phase=np.vdot(want,op);err=float(np.max(abs(op-phase/abs(phase)*want)));assert err<1e-10
    result=dict(**row,seed=seed,depth=sc[0],cx=sc[1],path=str(p),error=err);rows.append(result);print('native',{k:v for k,v in result.items() if k!='co'},flush=True)
 (outdir/'report.json').write_text(json.dumps(dict(moves=len(moves),steps=steps,seeds=seeds,history=history,rows=rows),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--steps',type=int,default=6000);p.add_argument('--seeds',type=int,default=20);a=p.parse_args();run(a.outdir,a.steps,a.seeds)
