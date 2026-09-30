import os,sys,pickle,json,subprocess,time,argparse
from pathlib import Path
from kdrv import KTERMS,CO,assemble
from ev116 import typed_windows,evaluate_kg
p=argparse.ArgumentParser();p.add_argument('--wide',action='store_true');args=p.parse_args()
ROOT=Path(os.environ['CLASSIQ_ROOT']);out=ROOT/'artifacts/rewrite117_20260922/defer';out.mkdir(exist_ok=True)
DX,DY,pl=pickle.load(open(ROOT/'src/post151_sa/sat116/champ117.pkl','rb'));seq,W,ST,rdy,unl=pl
svec=[26,37,42,43,28,40,42,44]
def decode(path,T,typed):
 lines=path.read_text().splitlines();d,t0=map(int,lines[0].split());rows=ST.copy();done=set();pend={};body=[]
 for i,m in enumerate(rows):
  if m in KTERMS:done.add(m);pend[i]=m
 zs,xs,zd,xd=typed_windows(T) if typed else (svec,rdy,[T-u for u in unl],[T-u for u in unl])
 for k in range(1,d+1):
  vals=list(map(int,lines[k].split()));layer=list(zip(vals[1::2],vals[2::2]));used={v for p in layer for v in p};tau=t0+k
  for c,t in layer:
   if t in pend:done.remove(pend.pop(t))
  for w in list(pend):
   if w not in used and zs[w]<tau<=zd[w]:body.append(('R',W[w],2*CO[pend.pop(w)]))
  for c,t in layer:
   assert zs[c]<tau<=zd[c] if typed else rdy[c]<tau<=T-unl[c]
   assert xs[t]<tau<=xd[t] if typed else rdy[t]<tau<=T-unl[t]
   rows[t]^=rows[c];body.append(('C',W[c],W[t]));m=rows[t]
   if m in KTERMS and m not in done:done.add(m);pend[t]=m
 assert done==set(KTERMS) and not pend and rows==ST,(len(done),pend,rows)
 return [('S',list(range(18)))]+body
records=[]
configs=[(117,4000,2,False),(116,4000,2,False),(116,4000,3,False),(116,4000,2,True),(117,4000,2,True),(116,16000,2,True)] if args.wide else [(117,300,2,False),(116,300,2,False),(116,300,3,False),(116,300,2,True),(117,300,2,True)]
for T,width,seed,typed in configs:
 name=f'T{T}_w{width}_s{seed}_typed{int(typed)}';f=out/(name+'.txt');env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',SRDY=','.join(map(str,svec)))
 if typed:
  for key,vs in zip(['ZS','XS','ZD','XD'],typed_windows(T)):env[key]=','.join(map(str,vs))
 inp='\n'.join([str(len(KTERMS)),' '.join(map(str,KTERMS))]+[f'{st} {r} {T-u}' for st,r,u in zip(ST,rdy,unl)])+'\n';start=time.monotonic()
 try:
  p=subprocess.run([str(ROOT/'src/post151_sa/c/kbeam_defer'),str(width),'65',str(seed),'0.02',str(f),'4','0'],input=inp,text=True,capture_output=True,env=env,timeout=100 if args.wide else 35)
  (out/(name+'.log')).write_text(p.stderr);row=dict(name=name,rc=p.returncode,seconds=time.monotonic()-start)
  if p.returncode==0:row['evaluation']=evaluate_kg(decode(f,T,typed),str(out/name),116,30)
 except subprocess.TimeoutExpired as exc:
  (out/(name+'.log')).write_text((exc.stderr or b'').decode() if isinstance(exc.stderr,bytes) else (exc.stderr or ''));row=dict(name=name,timeout=True,seconds=time.monotonic()-start)
 records.append(row);(out/('report.json' if args.wide else 'small_report.json')).write_text(json.dumps(records,indent=2));print(row,flush=True)
