"""Jointly change the reachable-code phase polynomial and resynthesize its network."""
import os,sys,json,pickle,subprocess,time,math
from pathlib import Path
import numpy as np
from kdrv import CO
from kgenco import build_F,CH
import ev116
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/phase_network117_20260922';out.mkdir(exist_ok=True)
DX,DY,pl=pickle.load(open(ROOT/'src/post151_sa/sat116/champ117.pkl','rb'));seq,W,ST,rdy,unl=pl
svec=[26,37,42,43,28,40,42,44];null={0:1,1:-1,4:-1,5:1,10:-1,11:1,14:1,15:-1}
co=CO.copy()
for m,v in null.items():co[m]+=math.pi*v/8
terms=[m for m in range(1,256) if abs(co[m])>1e-10];assert len(terms)==64
F,known=build_F();delta=CH.T@(co-CO);assert np.max(abs(delta[known]))<1e-12
np.save(out/'co64.npy',co)
ev116.CO=co;ev116.KTERMS=terms
records=[]
configs=[(117,4000,2,'kbeam_wirehash'),(116,4000,2,'kbeam_wirehash'),(116,4000,3,'kbeam_wirehash'),(117,16000,2,'kbeam_wirehash'),(116,16000,2,'kbeam_wirehash'),(116,16000,2,'kbeamV8')]
for T,width,seed,binary in configs:
 exe=ROOT/'src/post151_sa/c'/binary
 if not exe.exists():continue
 name=f't{T}_w{width}_s{seed}_{binary}';path=out/(name+'.txt');env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',SRDY=','.join(map(str,svec)))
 inp='\n'.join([str(len(terms)),' '.join(map(str,terms))]+[f'{st} {r} {T-u}' for st,r,u in zip(ST,rdy,unl)])+'\n';start=time.monotonic()
 try:
  p=subprocess.run([str(exe),str(width),'65',str(seed),'0.02',str(path),'4','0'],input=inp,text=True,capture_output=True,env=env,timeout=90);(out/(name+'.log')).write_text(p.stderr);r=dict(name=name,rc=p.returncode,seconds=time.monotonic()-start)
  if p.returncode==0:
   r['evaluation']=ev116.evaluate(str(path),svec,T,116,30)
   from classiq_synth.core.verify import exhaustive_verify
   q=Path(str(path).replace('.txt','_asm.qasm'));r['verification']=exhaustive_verify(q)
 except subprocess.TimeoutExpired as e:
  (out/(name+'.log')).write_text((e.stderr or b'').decode() if isinstance(e.stderr,bytes) else e.stderr or '');r=dict(name=name,status='TIMEOUT')
 records.append(r);(out/'report.json').write_text(json.dumps(records,indent=2));print(r,flush=True)
