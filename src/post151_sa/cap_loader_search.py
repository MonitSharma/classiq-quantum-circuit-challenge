"""Coordinate hard-cap x-loader search, preserving a champion prefix."""
import os,json,pickle,subprocess,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from lbeval2 import load_beam,sa4
from sim import check_loader2,symbolic_final
from kdrv import profile
from kgen import side_plan
OUT=Path('runs/caps_0924');OUT.mkdir(exist_ok=True)

def run(prefix,seed,width=6000,lx0=35):
    tag=f'asap_k{prefix}_s{seed}_w{width}_lx0{lx0}';dest=OUT/tag
    caps=[0]*15
    for code,cap in [(1,43),(2,lx0),(4,43),(12,44)]:caps[code-1]=cap
    env=dict(os.environ,CODECAP=','.join(map(str,caps)),WFRZ='0',WFT='.35',WFMAX='.7',
             FZMAX='4',WREACH2='.15',NP='18',WSPREAD='.6',SPCAP='3',
             BLKW='14,28,30,40,42,24,30,27,29,33,31,29,31,31,29',
             PREFIX='runs/t115_0923/loaders/champ_x.pfx',PREFIXK=str(prefix))
    st=time.monotonic()
    with open('runs/s118x.lb') as inp,open(str(dest)+'.log','w') as log:
        r=subprocess.run(['./c/lbeam_asap_caps',str(width),'32','49',str(seed),'16','.5',str(dest)+'.txt','.02'],stdin=inp,stderr=log,env=env)
    rec=dict(tag=tag,prefix=prefix,seed=seed,width=width,returncode=r.returncode,seconds=time.monotonic()-st)
    if r.returncode==0:
        D=pickle.load(open('runs/s118x.pkl','rb'));_,seq=load_beam(str(dest)+'.txt')
        d,pen,g=sa4(D,seq,tag='caps_'+tag,binary='./c/sa4');chk=check_loader2(g,D['newcode'])
        assert pen==0 and chk['max_dev']<1e-9
        e,_=profile(g);fx,w,coords,ready=side_plan(g,e,D,0,maxlen=0);assert not fx
        rows=symbolic_final(g)
        mapping={c:ready[i] for i,c in enumerate(coords)}
        assert all(mapping[c]<=cap for c,cap in [(1,43),(2,lx0),(4,43),(12,44)]),mapping
        D=dict(D,gates=g,fix=[],depth=max(e));pickle.dump(D,open(str(dest)+'.pkl','wb'))
        rec.update(ready=mapping,depth=max(e),max_dev=chk['max_dev'])
    Path(str(dest)+'.json').write_text(json.dumps(rec,indent=2));print(json.dumps(rec),flush=True)
    return rec
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs=[pool.submit(run,k,s) for k in [20,26,32,36] for s in [1,2]]
        for f in fs:f.result()
