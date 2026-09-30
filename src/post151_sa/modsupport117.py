"""Exact power-of-two modular linear solve for phases on visited kernel masks."""
import os,pickle,json,math
from pathlib import Path
import numpy as np

def solve_mod(A,b,mod):
 A=np.asarray(A,dtype=np.int64)%mod;b=np.asarray(b,dtype=np.int64)%mod
 nr,nc=A.shape;perm=np.arange(nc);r=0
 while r<min(nr,nc):
  pos=np.argwhere(A[r:,r:]%2)
  if not len(pos):break
  i,j=pos[0]+r
  if i!=r:A[[r,i]]=A[[i,r]];b[[r,i]]=b[[i,r]]
  if j!=r:A[:,[r,j]]=A[:,[j,r]];perm[[r,j]]=perm[[j,r]]
  inv=pow(int(A[r,r]),-1,mod);A[r]=(A[r]*inv)%mod;b[r]=(b[r]*inv)%mod
  if r+1<nr:
   c=A[r+1:,r].copy();A[r+1:]=(A[r+1:]-c[:,None]*A[r])%mod;b[r+1:]=(b[r+1:]-c*b[r])%mod
  r+=1
 if np.any(b[r:]%2):return None
 x=np.zeros(nc,dtype=np.int64)
 if mod>2 and r<nc:
  sub=solve_mod(A[r:,r:]//2,b[r:]//2,mod//2)
  if sub is None:return None
  x[r:]=sub
 elif np.any(b[r:]%mod):return None
 for i in range(r-1,-1,-1):x[i]=(b[i]-A[i,i+1:]@x[i+1:])%mod
 out=np.zeros(nc,dtype=np.int64);out[perm]=x
 return out

if __name__=='__main__':
 from kdrv import CO
 from kgenco import build_F,CH
 ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/rewrite117_20260922/modsupport';out.mkdir(exist_ok=True)
 F,known=build_F();pl,kg=pickle.load(open(ROOT/'src/post151_sa/runs/p6_117_16000_2.pkl','rb'));rows=dict(zip(pl[1],pl[2]));seen=set(rows.values())
 for g in kg:
  if g[0]=='C':rows[g[2]]^=rows[g[1]];seen.add(rows[g[2]])
 ms=sorted(seen);A=((1-CH[ms][:,known].T)//2).astype(int);a0=np.rint(CO[ms]/math.pi*32).astype(int);assert np.max(abs(a0/32*math.pi-CO[ms]))<1e-12;b=A@a0
 # Ignore common phase using differences from one reachable input.
 A=(A-A[0])%32;b=(b-b[0])%32
 sol=solve_mod(A,b,32);assert sol is not None and np.all((A@sol-b)%32==0)
 records=[]
 for i,m in enumerate(ms):
  if a0[i]==0:continue
  allowed=[j for j in range(len(ms)) if j!=i];sol=solve_mod(A[:,allowed],b,32)
  row=dict(mask=m,removable=sol is not None)
  if sol is not None:
   assert np.all((A[:,allowed]@sol-b)%32==0)
   co=np.zeros(256);co[np.array(ms)[allowed]]=sol/32*math.pi
   row['terms']=int(np.count_nonzero(sol));np.save(out/f'without_{m}.npy',co)
  records.append(row)
 print(records,flush=True);print('removable',sum(r['removable'] for r in records),'of',len(records),flush=True)
 (out/'report.json').write_text(json.dumps(records,indent=2))
