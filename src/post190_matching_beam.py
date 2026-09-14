"""Beam scheduler with explicit disjoint CX-matching enumeration."""
import itertools,json,math,random
from pathlib import Path
import numpy as np
import post218_beam_phase as pb
from qiskit import qasm2
from build_two_stage_196 import encoders,KERNEL_WIRES
from distributed_frame_search import native
from post196_free_ancilla_order import finish
from post258_joint_encoder_schedule import touches

def layers(st,rng,count,alpha,timew,noise,guard=0,fill=1):
 n=len(st.basis);masks=sorted(st.remaining);c=pb._coords_matrix(st.inv,masks);counts=c.sum(axis=0);coincide=c.T@c;low=min(st.times);edges=[]
 for a in range(n):
  for b in range(n):
   if a==b:continue
   new=st.basis[a]^st.basis[b]
   if not pb._legal(new,guard):continue
   hit=float(new in st.remaining);look=sum((new^st.basis[z]) in st.remaining for z in range(n) if z not in (a,b));late=max(st.times[a],st.times[b])-low
   value=alpha*hit+1.5*look-(counts[b]-2*coincide[a][b])-timew*late
   edges.append((value,a,b))
 edges.sort(reverse=True);edges=edges[:min(14,len(edges))];cands=[]
 for r in range(1,min(fill,3)+1):
  for combo in itertools.combinations(edges,r):
   if len({x for _,a,b in combo for x in (a,b)}) != 2*r:continue
   cands.append((sum(v for v,_,_ in combo),tuple((a,b) for _,a,b in combo)))
 cands.sort(key=lambda z:z[0]+rng.random()*noise,reverse=True);out=[]
 for _,lay in cands:
  if list(lay) not in out:out.append(list(lay))
  if len(out)>=count:break
 return out

def run(out,seeds=24):
 assert not out.exists();out.mkdir(parents=True);rec=json.loads(Path('artifacts/193_cx853/phase_search_recipe.json').read_text());co=np.asarray(rec['co'])*math.pi
 enc=encoders(json.loads(Path('artifacts/190/class_codes.json').read_text()),298,506);arrival=[touches(enc)[w] for w in KERNEL_WIRES];old=pb._layers;pb._layers=layers;best=(190,857);rows=[]
 try:
  for seed in range(seeds):
   rng=random.Random(seed+190991)
   def finalize(q,basis):
    initial=touches(q,arrival);win=None
    for sample in range(400):
     ops,perm,times=finish(basis,initial,rng,sample);score=(max(times[w]+arrival[col] for w,col in enumerate(perm)),len(ops)+q.size())
     if win is None or score<win[0]:win=(score,ops)
    score,ops=win;result=q.copy()
    for a,b in ops:result.cx(a,b)
    return score,result
   cfg=dict(seed=seed,beam=96,branch=18,alpha=6.0,timew=1.2,horizon=1.5,fill=3)
   k=pb.psynth(8,{m:float(co[m]) for m in range(1,256) if abs(co[m])>1e-10},global_phase=float(co[0]),finalize=finalize,**cfg)
   q=native(enc.compose(k,KERNEL_WIRES).compose(enc.inverse(),list(range(18))));text=qasm2.dumps(q);q=qasm2.loads(text);score=(q.depth(),q.count_ops().get('cx',0));row=dict(**cfg,depth=score[0],cx=score[1]);rows.append(row)
   if score<best:best=score;p=out/f'oracle_d{score[0]}_cx{score[1]}.qasm';p.write_text(text);row['path']=str(p);print('IMPROVEMENT',row,flush=True)
   if seed%4==0:print('seed',seed,'best',best,flush=True)
   (out/'report.json').write_text(json.dumps(dict(best=best,rows=rows),indent=2))
 finally:pb._layers=old
 print('done',best,flush=True)
if __name__=='__main__':run(Path('artifacts/post190_matching_beam_v1'))
