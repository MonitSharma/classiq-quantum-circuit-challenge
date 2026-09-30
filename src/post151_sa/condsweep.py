"""Support sizes for every valid conditional loading structure (star / seq / seq2 / mixed)."""
import sys, itertools, numpy as np
sys.path.insert(0,'.')
from codes import xcode, ycode, bits
from condlp import atoms_for, sparse_rep

def sizes(side, cols, cond):
    code = xcode if side=='x' else ycode
    B=bits(code)
    Bn=np.array([sum(B[i] for i in range(3) if cols[j]>>i&1)%2 for j in range(3)])
    out=[]
    for i in range(3):
        keys,A=atoms_for(Bn,cond[i])
        r=sparse_rep(np.pi*Bn[i].astype(float),A,iters=10)
        if r is None: return None
        out.append(len(r[0]))
    return out

for side, cols in (('x',(1,2,6)), ('y',(1,2,4))):
    print('===', side, cols)
    for cond in ({0:[],1:[0],2:[0]}, {0:[],1:[0],2:[0,1]}, {0:[],1:[0],2:[1]},
                 {0:[],1:[0],2:[]}, {0:[],1:[1],2:[0]}, {0:[],1:[0,1],2:[0,1]},
                 {0:[],1:[],2:[0,1]}, {0:[],1:[1],2:[1]}):
        s=sizes(side,cols,cond)
        print('  ', {k:''.join(map(str,v)) for k,v in cond.items()}, s, 'total', sum(s) if s else None, flush=True)
