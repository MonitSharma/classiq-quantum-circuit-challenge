import sys,os,glob,subprocess,json,time,pickle,numpy as np
from concurrent.futures import ThreadPoolExecutor
R=os.path.expanduser('~/mnt/classiq')
DX,DY,pl=pickle.load(open(R+'/src/post151_sa/sat116/champ117.pkl','rb')); seq,W,ST,rdy,unl=pl
files=[]
for fam in ['alternating','block_null','modular_blocks','null_family','plateau']:
    files+=sorted(glob.glob(R+f'/artifacts/phase_network117_20260922/{fam}/co_*.npy'))
T=int(sys.argv[1]); a=int(sys.argv[2]); b=int(sys.argv[3]); Wb=sys.argv[4]; seed=sys.argv[5]
env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',LAW='0.3',SRDY='26,37,42,43,28,40,42,44')
def job(f):
    co=np.load(f); terms=list(map(int,np.flatnonzero(abs(co)>1e-10)))
    if len(terms)>64: return (f,len(terms),'skip',None)
    tag=f.split('/')[-2]+'_'+os.path.basename(f)[:-4]
    inp='\n'.join([str(len(terms)),' '.join(map(str,terms))]+[f'{st} {r} {T-u}' for st,r,u in zip(ST,rdy,unl)])+'\n'
    try:
        p=subprocess.run(['./kbeam_lb',Wb,'65',seed,'0.02',f'scr_{tag}_{T}.out','4','0'],input=inp,text=True,capture_output=True,env=env,timeout=160)
        lines=[l for l in p.stderr.split('\n') if 'complete-dist' in l]
        best=None
        for l in lines:
            t=l.split(); d=int(t[1]); dist=int(t[-1]); done=int(t[6])
            if done==len(terms) and dist<99: best=(d,dist)
        return (tag,len(terms),p.returncode,best)
    except subprocess.TimeoutExpired:
        return (tag,len(terms),'TO',None)
with ThreadPoolExecutor(4) as ex:
    for r in ex.map(job,files[a:b]): print(json.dumps(r),flush=True)
