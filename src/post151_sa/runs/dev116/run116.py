import sys, os, subprocess, time, json
KT=open('../kin_117.txt').read().split('\n')[:2]
CH={'ST':[2,8,1,4,32,64,192,16],'RDY':[34,39,42,46,35,43,44,44],'UNL':[34,39,42,46,35,43,44,44],'SV':[26,37,42,43,28,40,42,44]}
VFZ=[31,39,42,46,31,43,44,44]; XRDY=[34,39,41,46,35,43,44,42]
BIN=os.path.expanduser('~/kbeamV8')
cfg=[l.split() for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
budget=float(sys.argv[2]) if len(sys.argv)>2 else 165
NP=int(sys.argv[3]) if len(sys.argv)>3 else 4
t0=time.time(); procs=[]
def launch(c):
    name,T,W,seed,mu,srdy,rl,tcap,ctrl,rdyo=c[:10]
    P=CH; kvs=[]
    for kv in c[10:]:
        if kv.startswith('PAIR='): P=json.load(open(kv[5:]))
        else: kvs.append(kv)
    ST,RDY,UNL,SV=P['ST'],P['RDY'],P['UNL'],P['SV']
    T=int(T); rl=[0]*8 if rl=='-' else list(map(int,rl.split(',')))
    rdy=RDY if rdyo=='-' else list(map(int,rdyo.split(',')))
    inp='\n'.join(KT+[f'{s} {r} {T-u+x}' for s,r,u,x in zip(ST,rdy,UNL,rl)])+'\n'
    env=dict(os.environ); env['SINGLES_PENDING']='1'; env['TOUCHBAD']='1'
    for k in ('ZS','XS','ZD','XD','SRDY','TCAP','CTRL_RDY','CXPEN','NOISE','PERMSET','WDL','LAW','KCH'): env.pop(k,None)
    if srdy=='TYPED':
        env['ZS']=','.join(map(str,VFZ)); env['XS']=','.join(map(str,XRDY))
        env['ZD']=','.join(str(T-v+a) for v,a in zip(VFZ,rl)); env['XD']=','.join(str(T-v+a) for v,a in zip(XRDY,rl))
    elif srdy=='SV': env['SRDY']=','.join(map(str,SV))
    elif srdy!='-': env['SRDY']=srdy
    if tcap!='-': env['TCAP']=tcap
    if ctrl=='1': env['CTRL_RDY']=env.get('SRDY',','.join(map(str,rdy)))
    for kv in kvs:
        k,v=kv.split('=',1); env[k]=v
    left=max(5,budget-(time.time()-t0))
    p=subprocess.Popen(['timeout',str(int(left)),BIN,W,'70',seed,mu,f'o_{name}.txt','4','0'],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env,text=True)
    p.stdin.write(inp); p.stdin.close(); return (name,p,time.time())
import os.path
queue=[c for c in cfg if not os.path.exists('done/'+c[0])]
os.makedirs('done',exist_ok=True)
while queue or procs:
    while queue and len(procs)<NP and time.time()-t0<budget-25: procs.append(launch(queue.pop(0)))
    if not queue and not procs: break
    time.sleep(0.5)
    for x in list(procs):
        if x[1].poll() is not None:
            print(x[0],'rc',x[1].returncode,'t',round(time.time()-x[2]),flush=True); procs.remove(x)
            if x[1].returncode in (0,2): open('done/'+x[0],'w').write(str(x[1].returncode))
    if time.time()-t0>budget-25 and not procs: break
print('left',len(queue),[c[0] for c in queue])
