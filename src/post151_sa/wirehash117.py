import os,sys,pickle,json,subprocess,time
from pathlib import Path
from kdrv import KTERMS
from ev116 import evaluate,typed_windows,build_kg_typed,evaluate_kg
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/rewrite117_20260922/wirehash';out.mkdir(exist_ok=True)
DX,DY,pl=pickle.load(open(ROOT/'src/post151_sa/sat116/champ117.pkl','rb'));_,W,ST,rdy,unl=pl
svec=[27,37,41,43,28,40,42,44]  # exact historical valuestable calculated below
from kdrv import full_gates

def valuestable(D):
 wt=[0]*9;lu=[False]*9;tgt=[-1]*9
 for x in full_gates(D):
  if x[0][0]=='cx':
   c,t=x[1:];m=max(wt[c],wt[t])+1;wt[c]=wt[t]=m;lu[c]=lu[t]=False;tgt[t]=m
  else:
   w=x[1]
   if not lu[w]:wt[w]+=1;lu[w]=True
 return tgt
sx=valuestable(DX);sy=valuestable(DY);svec=[sx[w] if w<9 else sy[w-9] for w in W]
print('svec',svec,flush=True)
records=[]
configs=[(117,4000,2,False),(116,4000,2,False),(116,4000,3,False),(116,4000,2,True),(117,4000,2,True),(116,16000,2,False)]
for T,width,seed,typed in configs:
 name=f'T{T}_w{width}_s{seed}_typed{int(typed)}';f=out/(name+'.txt');env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',SRDY=','.join(map(str,svec)))
 if typed:
  z,x,zd,xd=typed_windows(T)
  for key,vs in zip(['ZS','XS','ZD','XD'],[z,x,zd,xd]):env[key]=','.join(map(str,vs))
 inp='\n'.join([str(len(KTERMS)),' '.join(map(str,KTERMS))]+[f'{st} {r} {T-u}' for st,r,u in zip(ST,rdy,unl)])+'\n'
 start=time.monotonic()
 try:
  p=subprocess.run([str(ROOT/'src/post151_sa/c/kbeam_wirehash'),str(width),'65',str(seed),'0.02',str(f),'4','0'],input=inp,text=True,capture_output=True,env=env,timeout=100)
  (out/(name+'.log')).write_text(p.stderr);row=dict(name=name,rc=p.returncode,seconds=time.monotonic()-start)
  if p.returncode==0:
   if typed:row['evaluation']=evaluate_kg(build_kg_typed(pl,f,z,zd),str(out/name),116,20)
   else:row['evaluation']=evaluate(str(f),svec,T,116,20)
 except subprocess.TimeoutExpired as e:row=dict(name=name,timeout=True,seconds=time.monotonic()-start)
 records.append(row);(out/'report.json').write_text(json.dumps(records,indent=2));print(row,flush=True)
