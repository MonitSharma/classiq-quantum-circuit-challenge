import numpy as np
from codes import *
def cells_of(side, mask):
    cls = COLCLS if side=='x' else ROWCLS
    keys=sorted(set(((bin(v&mask).count('1'))%2, cls[v]) for v in range(64)))
    idx={k:i for i,k in enumerate(keys)}
    cellid=[idx[((bin(v&mask).count('1'))%2, cls[v])] for v in range(64)]
    return keys, np.array(cellid)
if __name__=="__main__":
    for side,mask in [('x',48),('y',32)]:
        keys,cid=cells_of(side,mask)
        nc=len(keys)
        # all functions on cells
        F=((np.arange(2**nc)[:,None]>>np.arange(nc)[None,:])&1)  # 2^nc x nc
        vals=F[:,cid]  # 2^nc x 64
        W=(1-2*vals)@H.T  # walsh
        supp=(np.abs(W)>0.5).sum(1) - (np.abs(W[:,0])>0.5)
        order=np.argsort(supp)
        print(side,"cells",nc,keys)
        hist=np.bincount(supp)
        print(" support histogram (support:count) ", {i:int(c) for i,c in enumerate(hist) if c})
        for k in order[:40]:
            f=F[k]; 
            print("  supp",supp[k],"cellfunc",''.join(map(str,f)), "ones on x:", [v for v in range(64) if vals[k][v]][:20])
