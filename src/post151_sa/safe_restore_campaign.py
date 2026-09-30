"""Retest relaxed-window kernels after correcting the layer restoration bound."""
import json, os, subprocess, time
from pathlib import Path
import numpy as np
import ev116
from classiq_synth.core.verify import exhaustive_verify
OUT=Path('../../artifacts/parity_preserved_20260923'); OUT.mkdir(exist_ok=True)
ev116.CO=np.load('../../artifacts/116/recipes/kernel_co.npy')
ev116.KTERMS=list(map(int,np.flatnonzero(abs(ev116.CO)>1e-10)))
svec=[26,37,42,43,28,40,42,44]
_,_,ST,rdy,unl=ev116.pl
for T,W,seed in [(116,4000,1),(116,16000,2),(115,4000,1),(115,8000,2),(115,16000,3),(115,16000,4)]:
    name=f'safe_v2_relaxed_t{T}_w{W}_s{seed}'; path=OUT/(name+'.txt')
    env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',SRDY=','.join(map(str,svec)))
    for key in ['ZS','XS','ZD','XD']: env.pop(key,None)
    inp='\n'.join([str(len(ev116.KTERMS)),' '.join(map(str,ev116.KTERMS))]+[f'{st} {r} {T-u}' for st,r,u in zip(ST,rdy,unl)])+'\n'
    start=time.monotonic()
    with open(OUT/(name+'.log'),'w') as log:
        p=subprocess.run(['./c/kbeam_typed_lb',str(W),'65',str(seed),'.02',str(path),'4','0'],input=inp,text=True,stderr=log,env=env)
    rec=dict(name=name,target=T,width=W,seed=seed,returncode=p.returncode,seconds=time.monotonic()-start)
    print(json.dumps(rec),flush=True)
    if p.returncode==0:
        rec['evaluation']=ev116.evaluate(str(path),svec,T,T,60)
        q=rec['evaluation'].get('qasm',str(path).replace('.txt','_asm.qasm'))
        rec['verification']=exhaustive_verify(q,write_report=True)
    (OUT/(name+'.json')).write_text(json.dumps(rec,indent=2)); print(json.dumps(rec),flush=True)
