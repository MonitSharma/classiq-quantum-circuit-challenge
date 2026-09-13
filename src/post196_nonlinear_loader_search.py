"""Bounded nonlinear coordinate preconditioning of the protected code loaders.

RCCX changes may leave input-dependent phases. The full encoder's actual
inverse cancels them around the diagonal kernel. Preserve its raw tag wire.
Frame bounds rank candidates only; serialized native circuits decide scores.
"""
import argparse,itertools,json,math
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Statevector
from post196_frame_balance import H6,SPLITS,FRAME_SHIFTS,TOUR,TOUCH,loader_floor
from post196_linear_loader_frames import relative_body
from distributed_ucry import structured_ucry
from distributed_frame_search import native
from post258_two_stage_anf import decode
from build_two_stage_196 import encoders,KERNEL_WIRES
from exhaustive_verify import exhaustive
import two_stage_oracle as ts

def bound_indices():
 out=[]
 for _,high in SPLITS:
  low=[i for i in range(6) if i not in high];frames=[]
  for shifts in FRAME_SHIFTS:
   frames.append([[64*i+sum((hp>>k&1)<<high[k] for k in range(3))+
                   sum((m>>k&1)<<low[k] for k in range(3)) for m in range(8)]
                  for i in range(3) for hp in (shifts[i],shifts[i]^(1<<i))])
  out.append(frames)
 return np.array(out)

INDEX=bound_indices();TOURS=np.array(TOUR);BUSY=TOURS+np.array([s.bit_count() for s in range(256)]);TOUCHES=np.array(TOUCH)
def bounds(values):
 tables=((values[:,None,:]>>np.arange(3)[None,:,None])&1).astype(float)
 spectrum=(abs(tables@H6)>1e-9).reshape(-1,192)
 subsets=np.sum(spectrum[:,INDEX]*(1<<np.arange(8)),axis=-1)
 host=BUSY[subsets].max(axis=-1);avg=(TOURS[subsets].sum(axis=-1)+2)//3
 cont=TOUCHES[subsets].sum(axis=-2).max(axis=-1)
 scores=np.maximum(np.maximum(host,avg),cont).sum(axis=-1)+13
 arg=scores.argmin(axis=-1)
 return scores[np.arange(len(scores)),arg],arg,spectrum.sum(axis=-1)

def pre_circuit(side,seq):
 q=QuantumCircuit(9)
 if side:q.cx(5,4)
 for a,b,t,pol in seq:
  for i,c in enumerate((a,b)):
   if pol>>i&1:q.x(c)
  q.rccx(a,b,t)
  for i,c in enumerate((a,b)):
   if pol>>i&1:q.x(c)
 return q

def run(out,levels,beam,seeds):
 assert not out.exists();out.mkdir(parents=True)
 codes=json.loads(Path('artifacts/196/class_codes.json').read_text());bags=[];reports=[]
 for side,cls,mask,key,protected in [(0,ts.ROWCLS,32,'ylab',5),(1,ts.COLCLS,48,'xlab',4)]:
  lab=decode(codes[key]);original=np.array([lab[((v&mask).bit_count()%2,c)] for v,c in enumerate(cls)])
  inputs=np.arange(64);baseperm=inputs^(((inputs>>5&1)<<4) if side else 0)
  initial=original[np.argsort(baseperm)]
  gateinfo=[]
  for t in range(6):
   if t==protected:continue
   for a,b in itertools.combinations([v for v in range(6) if v!=t],2):
    for pol in range(4):
     perm=inputs^(((((inputs>>a&1)^(pol&1))&((inputs>>b&1)^(pol>>1)))<<t))
     gateinfo.append(((a,b,t,pol),perm))
  frontier=[(initial,[],baseperm)];shortlist=[];seen=set();counts=[]
  for level in range(1,levels+1):
   candidates=[]
   for vals,seq,perm in frontier:
    for gate,gperm in gateinfo:
     if seq and tuple(seq[-1])==gate:continue
     nv=vals[gperm];np_=gperm[perm];signature=nv.tobytes()
     if signature in seen:continue
     seen.add(signature);candidates.append((nv,seq+[gate],np_))
   ranked=[]
   for start in range(0,len(candidates),32):
    chunk=candidates[start:start+32];floor,high,support=bounds(np.array([v[0] for v in chunk]))
    for item,f,h,s in zip(chunk,floor,high,support):
     # A ranking heuristic, never called a native-depth bound.
     ranked.append((int(f)+7*level,int(f),int(s),int(h),item))
   ranked.sort(key=lambda v:v[:3]);frontier=[r[-1] for r in ranked[:beam]]
   shortlist.extend(ranked[:8]);counts.append(len(ranked))
   print('screen',side,level,'candidates',len(ranked),'best rank/floor/support',ranked[0][:3],flush=True)
  retained=[];native_rows=[]
  for rank,floor,support,hi,(vals,seq,perm) in sorted(shortlist,key=lambda v:v[:3])[:16]:
   table=math.pi*((vals[None,:]>>np.arange(3)[:,None])&1)
   assert loader_floor(table)[0]==floor
   pre=pre_circuit(side,seq);opts=[]
   for seed in range(seeds):
    for sparse in (False,True):
     raw=structured_ucry(table,[6,7,8],list(range(6)),seed,high=SPLITS[hi][1],sparse=sparse,open_walk=not sparse)
     q=pre.compose(relative_body(raw));opts.append((q.depth(),q.size(),seed,sparse,q))
   for _,_,seed,sparse,raw in sorted(opts,key=lambda v:v[:2])[:2]:
    q=native(raw);error=0.
    # Exact-file component test, permitting its removable input phase.
    text=qasm2.dumps(q);q=qasm2.loads(text)
    for v in range(64):
     state=Statevector.from_int(v,512).evolve(q).data;w=int(perm[v])|(int(original[v])<<6)
     z=state[w];want=np.zeros(512,complex);want[w]=z/abs(z) if abs(z)>0 else 1
     error=max(error,float(max(abs(state-want))))
    assert error<1e-10,error
    meta=dict(depth=q.depth(),cx=int(q.count_ops().get('cx',0)),sequence=seq,frame_floor=floor,support=support,high=SPLITS[hi][1],seed=seed,sparse=sparse,error=error)
    retained.append((q,meta));native_rows.append(meta)
   print('compile',side,seq,'best',min(r[1]['depth'] for r in retained),flush=True)
  retained.sort(key=lambda r:(r[1]['depth'],r[1]['cx']));bags.append(retained[:4]);reports.append(dict(side=side,screen_counts=counts,candidates=native_rows))
  (out/f'encoder_{side}.qasm').write_text(qasm2.dumps(retained[0][0]));(out/'loaders.json').write_text(json.dumps(reports,indent=2))
 kern=qasm2.load('artifacts/196/kernel.qasm');rows=[];best=(196,858)
 for ey,my in bags[0]:
  for ex,mx in bags[1]:
   enc=QuantumCircuit(18);enc.compose(ey,ts.YW+ts.YA,inplace=True);enc.compose(ex,ts.XW+ts.XA,inplace=True)
   q=native(enc.compose(kern,KERNEL_WIRES).compose(enc.inverse()));score=(q.depth(),q.count_ops().get('cx',0))
   rows.append(dict(depth=score[0],cx=score[1],y=my,x=mx))
   if score<best:
    path=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';path.write_text(qasm2.dumps(q));exhaustive(path);best=score
 (out/'report.json').write_text(json.dumps(dict(best=best,full_candidates=rows),indent=2))
 print('complete',best,'best new full',min((r['depth'],r['cx']) for r in rows),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--levels',type=int,default=3);p.add_argument('--beam',type=int,default=16);p.add_argument('--seeds',type=int,default=6);a=p.parse_args();run(a.outdir,a.levels,a.beam,a.seeds)
