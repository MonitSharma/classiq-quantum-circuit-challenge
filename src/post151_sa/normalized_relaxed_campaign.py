"""Wire-basis-normalized kernel search with the verified replay's relaxed windows."""
import os,json,subprocess,time
import numpy as np
import ev116
from pathlib import Path
from classiq_synth.core.verify import exhaustive_verify
OUT=Path('../../artifacts/parity_preserved_20260923')
base=np.load('../../artifacts/116/recipes/kernel_co.npy'); original=ev116.pl
seq,W,ST,rdy,unl=original
transform=[]
for m in range(256):
    x=0
    for k in range(8):
        if m>>k&1:x^=ST[k]
    transform.append(x)
co=base[transform]; ev116.CO=co; ev116.KTERMS=list(map(int,np.flatnonzero(abs(co)>1e-10)))
ev116.pl=(seq,W,[1<<k for k in range(8)],rdy,unl)
svec=[26,37,42,43,28,40,42,44]
# Verify every phase value under the reversible change of coordinates.
for bits in range(256):
    actual=sum(((bits&st).bit_count()%2)<<k for k,st in enumerate(ST))
    a=sum(base[m]*(-1)**((bits&m).bit_count()%2) for m in range(256))
    b=sum(co[m]*(-1)**((actual&m).bit_count()%2) for m in range(256))
    assert abs(a-b)<1e-12
for T,seed in [(116,1),(115,1),(115,2)]:
    width=8000; name=f'safe_v2_normal_relaxed_t{T}_w{width}_s{seed}'; path=OUT/(name+'.txt')
    env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1',SRDY=','.join(map(str,svec)))
    inp='\n'.join([str(len(ev116.KTERMS)),' '.join(map(str,ev116.KTERMS))]+[f'{st} {r} {T-u}' for st,r,u in zip(ev116.pl[2],rdy,unl)])+'\n'
    start=time.monotonic()
    with open(OUT/(name+'.log'),'w') as log:
        p=subprocess.run(['./c/kbeam_typed_lb',str(width),'65',str(seed),'.02',str(path),'4','0'],input=inp,text=True,stderr=log,env=env)
    rec=dict(name=name,target=T,width=width,seed=seed,returncode=p.returncode,seconds=time.monotonic()-start)
    if p.returncode==0:
        rec['evaluation']=ev116.evaluate(str(path),svec,T,T,60)
        q=rec['evaluation'].get('qasm',str(path).replace('.txt','_asm.qasm'))
        rec['verification']=exhaustive_verify(q,write_report=True)
        np.save(OUT/(name+'_co.npy'),co)
    (OUT/(name+'.json')).write_text(json.dumps(rec,indent=2)); print(json.dumps(rec),flush=True)
