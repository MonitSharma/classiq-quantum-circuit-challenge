"""Anneal the known kernel schedule, allowing phase emission at any valid visit."""
import sys,os,json,pickle,subprocess,time
from pathlib import Path
from kdrv import KTERMS,CO,assemble
from ev116 import evaluate_kg
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/rewrite117_20260922/sa';out.mkdir(exist_ok=True)
DX,DY,pl=pickle.load(open(ROOT/'src/post151_sa/sat116/champ117.pkl','rb'));seq,W,ST,rdy,unl=pl;svec=[26,37,42,43,28,40,42,44]
ls=(ROOT/'src/post151_sa/runs/p6_117_16000_2.txt').read_text().splitlines();L,t0=map(int,ls[0].split());base=ls[1:]
def decode(path,T):
 ls=path.read_text().splitlines();n,ta=map(int,ls[0].split());rows=ST.copy();done=set();body=[]
 for d,line in enumerate(ls[1:]):
  v=list(map(int,line.split()));cx=list(zip(v[1::2],v[2::2]));used={w for p in cx for w in p};tau=ta+d+1
  for w in range(8):
   if w not in used and svec[w]<tau<=T-unl[w] and rows[w] in KTERMS and rows[w] not in done:
    m=rows[w];done.add(m);body.append(('R',W[w],2*CO[m]))
  for c,t in cx:rows[t]^=rows[c];body.append(('C',W[c],W[t]))
 assert done==set(KTERMS) and rows==ST,(len(done),rows)
 return [('S',list(range(18)))]+body
records=[]
for T,seed in [(117,1)]+[(116,s) for s in range(1,9)]:
 name=f'T{T}_s{seed}';f=out/(name+'.txt');inp='\n'.join([f'{len(KTERMS)} {t0} {L}',' '.join(map(str,KTERMS))]+[f'{ST[w]} {svec[w]} {rdy[w]} {T-unl[w]} {T-unl[w]}' for w in range(8)]+base)+'\n';start=time.monotonic()
 try:
  p=subprocess.run([str(ROOT/'src/post151_sa/c/beam_sa117'),'3000000',str(seed),str(f)],input=inp,text=True,capture_output=True,timeout=50);(out/(name+'.log')).write_text(p.stderr);r=dict(T=T,seed=seed,rc=p.returncode,seconds=time.monotonic()-start)
  if p.returncode==0:r['evaluation']=evaluate_kg(decode(f,T),str(out/name),116,20)
 except subprocess.TimeoutExpired:r=dict(T=T,seed=seed,timeout=True)
 records.append(r);(out/'report.json').write_text(json.dumps(records,indent=2));print(r,flush=True)
