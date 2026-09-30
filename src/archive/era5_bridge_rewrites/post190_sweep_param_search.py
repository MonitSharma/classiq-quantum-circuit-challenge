"""Search structured_ucry parameters for the protected code tables (both sides)."""
import sys, json, math, itertools, time; sys.path.insert(0,'src')
import numpy as np
import two_stage_oracle as ts
import distributed_ucry as d
from distributed_frame_search import native
def par(t,m): return bin(t&m).count('1')&1
rec=json.load(open('artifacts/190/class_codes.json'))
ylab={tuple(map(int,k.split(','))):v for k,v in rec['ylab'].items()}
xlab={tuple(map(int,k.split(','))):v for k,v in rec['xlab'].items()}
def tables(lab,cls,mask):
    code=[lab[(par(t,mask),cls[t])] for t in range(64)]
    return np.array([[math.pi*((code[t]>>b)&1) for t in range(64)] for b in range(3)])
YT=tables(ylab,ts.ROWCLS,rec['ymask']); XT=tables(xlab,ts.COLCLS,rec['xmask'])
best={}
t0=time.time()
highs=[list(h) for h in itertools.combinations(range(6),3)]
for name,T in (('y',YT),('x',XT)):
    b=None
    for seed in range(12):
        for hi in [None]+highs:
            for mode in ('open','closed','sparse'):
                if time.time()-t0>330: break
                try:
                    raw=d.structured_ucry(T,[6,7,8],list(range(6)),seed,high=hi,
                                          sparse=(mode=='sparse'),
                                          open_walk=(mode=='open'))
                except Exception:
                    continue
                c=native(raw); sc=(c.depth(), c.count_ops().get('cx',0))
                if b is None or sc<b[0]: b=(sc,seed,hi,mode); print(f'  {name}: depth {sc[0]} cx {sc[1]} seed {seed} high {hi} {mode}',flush=True)
    best[name]=b
    print(f'{name} BEST: depth {b[0][0]} cx {b[0][1]}  (seed {b[1]}, high {b[2]}, {b[3]})',flush=True)
print(f'\nprotected encoder measures 83 layers for both sides together')
print(f'per-side best found: y {best["y"][0][0]}, x {best["x"][0][0]} -> encoder = max = {max(best["y"][0][0],best["x"][0][0])}')
