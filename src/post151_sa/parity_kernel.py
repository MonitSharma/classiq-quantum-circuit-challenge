"""Search real parity-preserving loader pairs, then assemble and verify.

Typed windows are measured from native fused loader gates. They relax only
commuting operations; shared-wire resource conflicts still need the full MILP.
"""
import argparse, json, os, pickle, subprocess, time
from pathlib import Path
import numpy as np
import ev116
from build import loader_ops
from canc import kind
from kdrv import full_gates
from kgen import plan
from postopt import fuse, parse_ops, depth, write
from canc import simplify
from classiq_synth.core.verify import exhaustive_verify

ROOT = Path(os.environ['CLASSIQ_ROOT'])
OUT = ROOT / 'artifacts/parity_preserved_20260923'

def windows(DX, DY, pl, target):
    seq, wires, _, _, _ = pl
    ops = loader_ops(full_gates(DX), list(range(9)))
    ops += loader_ops(full_gates(DY), list(range(9,18)))
    ops += [('cx', c, t) for c,t in seq]
    native = fuse([('cx',(o[1],o[2]),None) if o[0]=='cx'
                   else ('u3',(o[1],),o[2]) for o in ops])
    clocks=[0]*18; zs=[0]*18; xs=[0]*18
    for op in native:
        tau=max(clocks[w] for w in op[1])+1
        for w in op[1]: clocks[w]=tau
        if op[0]=='cx':
            c,t=op[1]; xs[c]=tau; zs[t]=tau
        else:
            w=op[1][0]; typ=kind(op[2])
            if typ!='Z': zs[w]=tau
            if typ!='X': xs[w]=tau
    z=[zs[w] for w in wires]; x=[xs[w] for w in wires]
    return z,x,[target-a for a in z],[target-a for a in x]

def run(xpath, ypath, target, width, seed, label, tlim, normalize=False, binary='./c/kbeam_lb'):
    champion=pickle.load(open(ROOT/'artifacts/116/recipes/loaders_plan.pkl','rb'))
    DX=champion[0] if xpath=='champ' else pickle.load(open(xpath,'rb'))
    DY=champion[1] if ypath=='champ' else pickle.load(open(ypath,'rb'))
    pl=plan(DX,DY)
    zs,xs,zd,xd=windows(DX,DY,pl,target)
    co=np.load(ROOT/'artifacts/116/recipes/kernel_co.npy')
    original_plan=pl
    if normalize:
        # Measure restoration in the actual starting-wire basis. The old
        # Hamming heuristic unfairly assigns two bits to a mixed code row.
        basis=pl[2]
        transform=[]
        for mask in range(256):
            row=0
            for k in range(8):
                if mask>>k&1: row ^= basis[k]
            transform.append(row)
        assert len(set(transform))==256
        co=co[transform]
        pl=(pl[0],pl[1],[1<<k for k in range(8)],pl[3],pl[4])
    terms=list(map(int,np.flatnonzero(abs(co)>1e-10)))
    tag=f'{label}_t{target}_w{width}_s{seed}'; path=OUT/(tag+'.txt')
    rec=dict(tag=tag,x=str(xpath),y=str(ypath),target=target,plan=pl,original_plan=original_plan,normalize=normalize,binary=binary,
             zs=zs,xs=xs,zd=zd,xd=xd)
    env=dict(os.environ,SINGLES_PENDING='1',TOUCHBAD='1')
    env.update({k:','.join(map(str,v)) for k,v in [('ZS',zs),('XS',xs),('ZD',zd),('XD',xd)]})
    inp='\n'.join([str(len(terms)),' '.join(map(str,terms))]+
                  [f'{row} {min(z,x)} {max(a,b)}' for row,z,x,a,b in zip(pl[2],zs,xs,zd,xd)])+'\n'
    print(json.dumps(rec),flush=True); start=time.monotonic()
    with open(OUT/(tag+'.log'),'w') as log:
        p=subprocess.run([binary,str(width),str(target),str(seed),'.02',str(path),'4','0'],
                         input=inp,text=True,stderr=log,env=env)
    rec.update(returncode=p.returncode,beam_seconds=time.monotonic()-start)
    if p.returncode==0:
        ev116.DX,ev116.DY,ev116.pl=DX,DY,pl
        ev116.CO,ev116.KTERMS=co,terms
        kg=ev116.build_kg_typed(pl,path,zs,zd)
        pickle.dump((DX,DY,pl),open(OUT/(tag+'_loaders.pkl'),'wb'))
        np.save(OUT/(tag+'_co.npy'),co)
        rec['evaluation']=ev116.evaluate_kg(kg,str(OUT/tag),target,tlim)
        qasm=rec['evaluation'].get('qasm',str(OUT/tag)+'_asm.qasm')
        rec['verification']=exhaustive_verify(qasm,write_report=True)
    (OUT/(tag+'.json')).write_text(json.dumps(rec,indent=2))
    print(json.dumps(rec),flush=True)
    return rec

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('x'); p.add_argument('y')
    p.add_argument('--target',type=int,default=115); p.add_argument('--width',type=int,default=4000)
    p.add_argument('--seeds',default='1'); p.add_argument('--label',required=True)
    p.add_argument('--tlim',type=float,default=60); a=p.parse_args()
    OUT.mkdir(exist_ok=True)
    for s in a.seeds.split(','): run(a.x,a.y,a.target,a.width,int(s),a.label,a.tlim)
