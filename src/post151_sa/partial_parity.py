"""Finite campaign: reuse parity targets early, preserve a code row after a deadline."""
import concurrent.futures, json, os, pickle, subprocess, time
from pathlib import Path
from lbeval2 import load_beam, sa4
from sim import check_loader2, symbolic_final
from kdrv import profile
from kgen import side_plan, plan
from parity_kernel import windows
OUT=Path('runs/partial_parity_0923'); OUT.mkdir(exist_ok=True)
CH=pickle.load(open('../../artifacts/116/recipes/loaders_plan.pkl','rb'))

def run(side,after,seed,width=3000,maxd=47,wp=2,by=None,balanced=False):
    by=after+6 if by is None else by
    tag=f'{side}_a{after}_b{by}_s{seed}_w{width}_d{maxd}_p{wp}'+('_balanced' if balanced else '')
    dest=OUT/tag; start=time.monotonic()
    env=dict(os.environ,PROTECT_TARGET='0',PARITYROW=str(48 if side=='x' else 32),
             LOCK_AFTER=str(after),LOCK_BY=str(by),WP=str(wp),WFRZ='0',WFT='.35',WFMAX='.7',
             FZMAX='3',WREACH2='.15',NP='18',WSPREAD='.6',SPCAP='3',
             BLKW='1,60,60,1,1,1,1,60,1,1,1,60,1,1,1')
    env.pop('PREFIX',None); env.pop('PREFIXK',None)
    if balanced:
        env['BLKW']=('14,28,30,40,42,24,30,27,29,33,31,29,31,31,29' if side=='x'
                     else '32,28,44,24,32,26,34,34,32,30,32,32,30,30,32')
    with open(f'runs/s118{side}.lb') as inp,open(str(dest)+'.log','w') as log:
        p=subprocess.run(['./c/lbeam_partial',str(width),'24',str(maxd),str(seed),'16','.5',str(dest)+'.txt','.02'],
                         stdin=inp,stderr=log,env=env)
    rec=dict(tag=tag,side=side,after=after,by=by,returncode=p.returncode,seconds=time.monotonic()-start)
    if p.returncode==0:
        D=pickle.load(open(f'runs/s118{side}.pkl','rb')); _,seq=load_beam(str(dest)+'.txt')
        d,pen,g=sa4(D,seq,tag=tag,binary='./c/sa4'); chk=check_loader2(g,D['newcode'])
        assert pen==0 and chk['max_dev']<1e-9
        D=dict(D,gates=g,fix=[],depth=d); prof,_=profile(g)
        fx,w,coords,ready=side_plan(g,prof,D,0,maxlen=0); assert not fx
        pair=[D,CH[1]] if side=='x' else [CH[0],D]
        pl=plan(*pair); zs,xs,_,_=windows(*pair,pl,115)
        rec.update(depth=max(prof),ready=ready,coords=coords,zs=zs,xs=xs,max_dev=chk['max_dev'])
        rec['pickle']=str(dest)+'.pkl'; pickle.dump(D,open(rec['pickle'],'wb'))
    Path(str(dest)+'.json').write_text(json.dumps(rec,indent=2)); print(json.dumps(rec),flush=True)
    return rec

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fs=[pool.submit(run,side,after,seed) for after in [16,24,32] for side in ['y','x'] for seed in [1,2]]
        for f in concurrent.futures.as_completed(fs): f.result()
