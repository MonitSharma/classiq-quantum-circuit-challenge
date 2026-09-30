"""Compile alternative 63-term phase representations under loader windows."""
import os,sys,json,pickle,subprocess,time,argparse
from pathlib import Path
import numpy as np
import ev116
from classiq_synth.core.verify import exhaustive_verify
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/phase_network117_20260922/block_network';out.mkdir(exist_ok=True)
DX,DY,pl=pickle.load(open(ROOT/'src/post151_sa/sat116/champ117.pkl','rb'));seq,W,ST,rdy,unl=pl;svec=[26,37,42,43,28,40,42,44]
p=argparse.ArgumentParser();p.add_argument('--family',choices=['block_null','alternating','plateau','modular_blocks','wide','continuous'],default='block_null');p.add_argument('--width',type=int,default=4000);p.add_argument('--target',type=int,default=116);p.add_argument('--indices',default='7,3,6,2,5,1,4');p.add_argument('--seed',type=int,default=2);p.add_argument('--binary',choices=['kbeam_wirehash','kbeam128'],default='kbeam_wirehash');p.add_argument('--mu',type=float,default=.02);p.add_argument('--law',type=float,default=.3);args=p.parse_args()
records=[];report=out/f'report_{args.family}_T{args.target}_W{args.width}_s{args.seed}_idx{args.indices.replace(",","-")}.json'
for index in map(int,args.indices.split(',')):
 co=np.load(ROOT/f'artifacts/phase_network117_20260922/{args.family}/co_{index}.npy');terms=list(map(int,np.flatnonzero(abs(co)>1e-10)));assert 0<len(terms)<=128
 ev116.CO=co;ev116.KTERMS=terms;T=args.target;width=args.width;seed=args.seed;name=f'{args.family}_co{index}_t{T}_w{width}_s{seed}_mu{args.mu}_law{args.law}';path=out/(name+'.txt');env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',SRDY=','.join(map(str,svec)),LAW=str(args.law))
 inp='\n'.join([str(len(terms)),' '.join(map(str,terms))]+[f'{st} {r} {T-u}' for st,r,u in zip(ST,rdy,unl)])+'\n';start=time.monotonic()
 try:
  binary='kbeam128' if len(terms)>64 else args.binary
  p=subprocess.run([str(ROOT/'src/post151_sa/c'/binary),str(width),'65',str(seed),str(args.mu),str(path),'4','0'],input=inp,text=True,capture_output=True,env=env,timeout=150);(out/(name+'.log')).write_text(p.stderr);r=dict(name=name,binary=binary,terms=len(terms),mu=args.mu,law=args.law,rc=p.returncode,seconds=time.monotonic()-start)
  if p.returncode==0:
   r['evaluation']=ev116.evaluate(str(path),svec,T,T,30);q=Path(str(path).replace('.txt','_asm.qasm'));r['verification']=exhaustive_verify(q)
   if r['evaluation'].get('qasm'):r['final_verification']=exhaustive_verify(r['evaluation']['qasm'])
 except subprocess.TimeoutExpired as e:
  (out/(name+'.log')).write_text((e.stderr or b'').decode() if isinstance(e.stderr,bytes) else e.stderr or '');r=dict(name=name,status='TIMEOUT')
 records.append(r);report.write_text(json.dumps(records,indent=2));print(r,flush=True)
 if r.get('final_verification',{}).get('depth',999)<116:break
