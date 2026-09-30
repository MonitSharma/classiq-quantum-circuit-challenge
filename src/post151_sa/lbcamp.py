"""Device loader campaign: run lbeam4c configs in parallel (<=165s), evaluate code-wire ready vectors.
usage: python3 lbcamp.py cfgfile budget   ; cfg line: tag side maxd W seed WFT WFMAX WREACH2 NP [ENV=VAL ...]"""
import sys, os, subprocess, time, json, pickle
sys.path.insert(0,'.')
cfg=[l.split() for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
budget=float(sys.argv[2]); t0=time.time()
os.makedirs('runs/lbc',exist_ok=True)
BL={'y':'32,28,44,24,32,26,34,34,32,30,32,32,30,30,32','x':'14,28,30,40,42,24,30,27,29,33,31,29,31,31,29'}
TG={'y':'42,34,99,46,99,99,99,39,99,99,99,99,99,99,99','x':'44,35,99,43,99,99,99,44,99,99,99,44,99,99,99'}
done=set(l.split()[0] for l in open('runs/lbc/results.txt')) if os.path.exists('runs/lbc/results.txt') else set()
queue=[c for c in cfg if c[0] not in done]; procs=[]
def launch(c):
    tag,side,md,W,seed,wft,wfm,wr2,npp=c[:9]
    env=dict(os.environ); env.update(dict(SINGLES_PENDING='1',BLKW=BL[side],WFRZ='0',FZMAX='3',NP=npp,WSPREAD='0.5',SPCAP='3',CONT='1',TGT=TG[side],WFT=wft,WFMAX=wfm,WREACH2=wr2))
    for kv in c[9:]: k,v=kv.split('=',1); env[k]=v
    left=int(budget-(time.time()-t0)-20)
    out=f'runs/lbc/{tag}.txt'
    p=subprocess.Popen(['timeout',str(max(left,10)),os.path.expanduser('~/lbeam4c'),W,'24',md,seed,'16','0.5',out,'0.02'],stdin=open(f'runs/s118{side}.lb'),stdout=subprocess.DEVNULL,stderr=open(f'runs/lbc/{tag}.err','w'),env=env)
    return (tag,side,p)
while queue and len(procs)<4: procs.append(launch(queue.pop(0)))
for tag,side,p in procs: p.wait()
from lbeval2 import load_beam, sa4
from sim import check_loader2
from kdrv import profile
from kgen import side_plan
R='../../artifacts/118/recipes/'
BASE={'x':'x_loader_d44','y':'y_loader_d46_blkw'}
with open('runs/lbc/results.txt','a') as f:
    for tag,side,p in procs:
        rc=p.returncode; line=f'{tag} {side} rc={rc}'
        if rc==0:
            try:
                D=pickle.load(open(R+BASE[side]+'.pkl','rb')); bd,seq=load_beam(f'runs/lbc/{tag}.txt')
                d,pen,g=sa4(D,seq,tag='lbc'+tag,binary='./c/sa4'); ok=pen==0 and check_loader2(g,D['newcode'])['max_dev']<1e-9
                e,_=profile(g); fx,Wv,co,rdy=side_plan(g,e,D,0)
                line+=f' ok={ok} code={dict(zip(co,rdy))} fix={len(fx)} depth={max(e)}'
            except Exception as ex: line+=f' ERR {ex!r}'
        f.write(line+'\n'); print(line,flush=True)
