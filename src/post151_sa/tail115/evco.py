import sys, os, json, re, numpy as np
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
os.environ.setdefault('CLASS_CODES','/work/classiq/artifacts/185/class_codes.json'); os.environ.setdefault('CLASSIQ_ROOT','/work/classiq')
import ev116, kdrv, smilp
from postopt import parse_ops, fuse, depth, write
from canc import simplify
SV=[26,37,42,43,28,40,42,44]
def run(co_path, beam, Tm, targets, tlim=120):
    co=np.load(co_path); ev116.CO=co; ev116.KTERMS=list(map(int,np.flatnonzero(abs(co)>1e-10))); kdrv.CO=co
    kg=ev116.build_kg_s(ev116.pl, beam, SV, Tm)
    q=beam.replace('.out','_asm.qasm'); d0,cx0=ev116.assemble(ev116.DX,ev116.DY,kg,q)
    ops=fuse(simplify(fuse(parse_ops(q)),verbose=False))
    res=dict(beam=os.path.basename(beam),asm_depth=d0,asm_cx=cx0,simp_cx=sum(1 for o in ops if o[0]=='cx'),simp_depth=depth(ops))
    for TT in targets:
        out=smilp.solve(ops,TT,tlim=tlim,verbose=False)
        res['T%d'%TT]=out is not None
        if out is not None:
            f=fuse(out); path=beam.replace('.out',f'_m{TT}.qasm'); write(f,path); res['qasm%d'%TT]=path; res['sched%d'%TT]=depth(f)
            break
    return res
if __name__=='__main__':
    Tm=int(sys.argv[1]); targets=list(map(int,sys.argv[2].split(',')))
    for b in sys.argv[3:]:
        b=os.path.abspath(b) if not b.startswith('/') else b
        m=re.match(r'g_(.*)_T\d+_s\d+\.out',os.path.basename(b))
        co=os.path.join(os.path.dirname(b),m.group(1)+'.npy') if m else os.environ['CO']
        try: print(json.dumps(run(co,b,Tm,targets)),flush=True)
        except Exception as e: print(json.dumps(dict(beam=b,err=repr(e))),flush=True)
