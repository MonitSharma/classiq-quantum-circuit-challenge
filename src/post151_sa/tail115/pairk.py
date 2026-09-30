"""Assemble given kernel schedules for a loader pair and run exact MILP. usage: pairk.py DX DY Tmodel outs..."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)).split('/tail115')[0] + '/tail115'); from localpaths import ROOT, PS, WK, KISSAT, MARCH, CADICAL  # local paths
import sys, os, pickle, json, numpy as np
import paireval as P
import ev116, kdrv, smilp
from postopt import parse_ops, fuse, depth, write
from canc import simplify
DX=P.load(sys.argv[1],0); DY=P.load(sys.argv[2],1); Tm=int(sys.argv[3])
co=np.load(os.environ.get('CO',f'{ROOT}/artifacts/116/recipes/kernel_co.npy')); terms=[int(m) for m in np.flatnonzero(abs(co)>1e-10) if m]
ev116.CO=co; ev116.KTERMS=terms; kdrv.CO=co
pl,srdy=P.windows(DX,DY)
for out in sys.argv[4:]:
    try:
        kg=ev116.build_kg_s(pl,out,srdy,Tm)
        q=out.replace('.out','_asm.qasm'); d0,cx0=ev116.assemble(DX,DY,kg,q)
        ops=fuse(simplify(fuse(parse_ops(q)),verbose=False)); ncx=sum(1 for o in ops if o[0]=='cx')
        r=[os.path.basename(out),'asm',d0,'cx',ncx]
        for TT in (115,116):
            sol=smilp.solve(ops,TT,tlim=300,verbose=False); r+=[TT,sol is not None]
            if sol is not None:
                f=fuse(sol); path=out.replace('.out',f'_m{TT}.qasm'); write(f,path); r+=[path]; break
        print(*r,flush=True)
    except Exception as e: print(out,'ERR',repr(e),flush=True)
