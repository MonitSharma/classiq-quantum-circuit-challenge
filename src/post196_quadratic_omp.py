"""Implicit overcomplete sign-dictionary search after six parallel ANDs.
FWHT correlations cover all 262144 feature parities without a huge matrix.
Orthogonal matching pursuit is a heuristic; a nonzero residual is no solution.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.linalg import solve_triangular
from two_stage_oracle import logo

def fwht(a):
 a=a.copy();h=1
 while h<len(a):
  v=a.reshape(-1,2*h);lo=v[:,:h].copy();hi=v[:,h:].copy();v[:,:h]=lo+hi;v[:,h:]=lo-hi;h*=2
 return a

def run(outdir,steps,pairing):
 assert not outdir.exists();outdir.mkdir(parents=True);started=time.monotonic()
 pairs=list(zip(range(0,12,2),range(1,12,2))) if pairing=='adjacent' else list(zip(range(6),range(6,12)))
 w=np.arange(4096,dtype=np.int64);features=w.copy()
 for i,(a,b) in enumerate(pairs):features|=(((w>>a)&1)&((w>>b)&1))<<(12+i)
 target=np.array([int(logo(int(v&63),int(v>>6))) for v in w],float)
 Q=np.zeros((4096,steps+1),order='F');R=np.zeros((steps+1,steps+1));Q[:,0]=1/64;R[0,0]=64
 residual=target-target.mean();selected=[0];history=[]
 for step in range(1,steps+1):
  extended=np.zeros(1<<18);extended[features]=residual;correlation=fwht(extended);correlation[selected]=0
  mask=int(np.argmax(abs(correlation)));vector=1.-2.*(np.bitwise_count(features&mask)%2).astype(float)
  proj=Q[:,:step].T@vector;v=vector-Q[:,:step]@proj
  correction=Q[:,:step].T@v;proj+=correction;v-=Q[:,:step]@correction
  norm=np.linalg.norm(v);assert norm>1e-7,(step,mask,norm)
  Q[:,step]=v/norm;R[:step,step]=proj;R[step,step]=norm;selected.append(mask)
  residual-=Q[:,step]*np.dot(Q[:,step],residual)
  maximum=float(max(abs(residual)));l2=float(np.linalg.norm(residual))
  if step%50==0 or maximum<1e-10:
   row=dict(terms=step,max_residual=maximum,l2=l2,seconds=time.monotonic()-started);history.append(row);print(row,flush=True)
   (outdir/'progress.json').write_text(json.dumps(dict(pairing=pairing,history=history),indent=2))
  if maximum<1e-10:break
 coefficients=solve_triangular(R[:step+1,:step+1],Q[:,:step+1].T@target)
 reconstruction=np.zeros(4096)
 for mask,co in zip(selected,coefficients):reconstruction+=co*(1.-2.*(np.bitwise_count(features&mask)%2).astype(float))
 error=float(max(abs(reconstruction-target)));exact=error<1e-10
 report=dict(pairing=pairing,pairs=pairs,terms=step,exact=exact,error=error,history=history,coefficients=list(zip(selected,coefficients.tolist())))
 (outdir/'report.json').write_text(json.dumps(report,indent=2));print('complete',step,exact,error,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--steps',type=int,default=700);p.add_argument('--pairing',choices=['adjacent','cross'],default='adjacent');a=p.parse_args();run(a.outdir,a.steps,a.pairing)
