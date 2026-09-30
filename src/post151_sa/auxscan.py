import numpy as np, itertools, sys, pickle
from codes import *
from cells import cells_of
from condlp import atoms_for, sparse_rep
side=sys.argv[1]; mask=48 if side=='x' else 32
keys,cid=cells_of(side,mask); nc=len(keys)
F=((np.arange(2**nc)[:,None]>>np.arange(nc)[None,:])&1)
vals=F[:,cid]
Hf=H.astype(float)
W=(1-2*vals)@Hf.T
supp=(np.abs(W)>0.5).sum(1)-(np.abs(W[:,0])>0.5)
code = xcode if side=='x' else ycode; B=bits(code)
# all 7 nonzero frame combos of label bits
labels={c:(sum(B[i] for i in range(3) if c>>i&1)%2) for c in range(1,8)}
def cond_support(target_bits, cond_bits_list):
    Bn=np.array([target_bits]+cond_bits_list)
    keys_,A=atoms_for(Bn,list(range(1,len(cond_bits_list)+1)))
    sup,sol=sparse_rep(np.pi*Bn[0].astype(float),A,iters=6)
    return len(sup)
order=[f for f in np.argsort(supp) if supp[f]>=3 and F[f][0]==0]
res=[]
for f in order[:40]:
    a=vals[f]
    best=min((cond_support(labels[c],[a]),c) for c in range(1,8))
    res.append((best[0],int(supp[f]),int(f),best[1]))
    print("aux f",f,"supp",supp[f],"best label|aux",best,flush=True)
res.sort(); print("TOP",res[:8])
