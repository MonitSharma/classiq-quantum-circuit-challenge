"""Search coupled four-input sign bases after six parallel pairwise ANDs.
Column exchanges use exact dyadic pivots and verify phase agreement on all
4096 inputs. This is a representation screen, not a claimed native oracle.
"""
import argparse,itertools,json,random,time
from pathlib import Path
import numpy as np
from two_stage_oracle import logo
from post196_quadratic_tensor import axis_apply,mod
F=np.array([v|(((v&1)*((v>>1)&1))<<4)|((((v>>2)&1)*((v>>3)&1))<<5) for v in range(16)])
S=np.array([[(-1)**((int(f)&m).bit_count()%2) for m in range(64)] for f in F],float)
def run(outdir,restarts):
 assert not outdir.exists();outdir.mkdir(parents=True);rng=np.random.default_rng(140);best=4097;records=[]
 for restart in range(restarts):
  if restart<4:groups=[list(range(4)),list(range(4,8)),list(range(8,12))]
  elif restart<8:groups=[[0,1,6,7],[2,3,8,9],[4,5,10,11]]
  else:groups=rng.permutation(12).reshape(3,4).tolist()
  polarity=0 if restart==0 else 4095 if restart==1 else int(rng.integers(4096))
  anf=np.array([int(logo((w^polarity)&63,(w^polarity)>>6)) for w in range(4096)])
  for bit in range(12):
   for w in range(4096):
    if w>>bit&1:anf[w]^=anf[w^(1<<bit)]
  lifted=anf.copy()
  if restart>=2:lifted*=rng.choice([-1,1],4096)
  for bit in range(12):
   for w in range(4096):
    if w>>bit&1:lifted[w]+=lifted[w^(1<<bit)]
  tensor=np.zeros((16,)*3)
  for idx in np.ndindex(tensor.shape):
   w=sum(((v>>i)&1)<<bit for v,group in zip(idx,groups) for i,bit in enumerate(group));tensor[idx]=lifted[w^polarity]
  bases=[list(range(16)) for _ in range(3)];invs=[S[:,:16].T/16 for _ in range(3)];co=tensor.copy()
  for axis in range(3):co=axis_apply(co,invs[axis],axis)
  # Alternate greedy exchanges with phase-equivalent modular reductions.
  for sweep in range(60):
   current=np.count_nonzero(co);bestmove=None;axes=rng.permutation(3)
   for axis in axes:
    flat=np.moveaxis(co,axis,0).reshape(16,-1);coords=invs[axis]@S
    for j in rng.permutation(16):
     allowed=[m for m in range(64) if m not in bases[axis] and abs(coords[j,m]) in (.25,.5,1.,2.,4.)]
     if not allowed:continue
     u=coords[:,allowed].T;row=flat[j][None,:]/u[:,j,None]
     candidates=flat[None,:,:]-u[:,:,None]*row[:,None,:];candidates[:,j,:]=row
     candidates=mod(candidates);scores=np.count_nonzero(abs(candidates)>1e-10,axis=(1,2))
     low=int(scores.min());choices=np.flatnonzero(scores==low);choice=int(rng.choice(choices))
     if low<current and (bestmove is None or low<bestmove[0]):bestmove=(low,axis,int(j),allowed[choice],candidates[choice].copy(),u[choice].copy())
   if bestmove is None:break
   _,axis,j,m,flat,u=bestmove
   row=invs[axis][j].copy()/u[j];invs[axis]-=u[:,None]*row[None,:];invs[axis][j]=row;bases[axis][j]=m
   co=np.moveaxis(flat.reshape((16,)*3),0,axis)
  count=int(np.count_nonzero(abs(co)>1e-10))
  if count<best:
   recon=co.copy()
   for axis in range(3):recon=axis_apply(recon,S[:,bases[axis]],axis)
   diff=recon-tensor;error=float(np.max(abs((diff-diff.flat[0]+1)%2-1)));assert error<1e-9,error
   best=count;row=dict(restart=restart,polarity=polarity,groups=groups,bases=bases,support=count,error=error,coefficients=co.tolist());records.append(row)
   (outdir/'best.json').write_text(json.dumps(row));print('block basis',restart,count,error,flush=True)
 (outdir/'report.json').write_text(json.dumps(dict(restarts=restarts,best=best,records=[{k:v for k,v in r.items() if k!='coefficients'} for r in records]),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--restarts',type=int,default=12);a=p.parse_args();run(a.outdir,a.restarts)
