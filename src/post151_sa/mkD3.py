import sys, pickle, numpy as np
from codes import *
from condlp import atoms_for, sparse_rep
def makeD(side, cols, cond, iters=10):
    code = xcode if side=='x' else ycode
    B=bits(code)
    Bn=np.array([sum(B[i] for i in range(3) if cols[j]>>i&1)%2 for j in range(3)])
    newcode=[int(Bn[0][v]|(Bn[1][v]<<1)|(Bn[2][v]<<2)) for v in range(64)]
    targets={}
    for i in range(3):
        keys,A=atoms_for(Bn,cond[i])
        r=sparse_rep(np.pi*Bn[i].astype(float),A,iters=iters)
        if r is None: return None
        sup,sol=r
        par={}
        for k,coef in zip(sup,sol):
            s,sub=keys[k]; mask=(1<<(6+i))|s
            for j in sub: mask|=1<<(6+j)
            par[mask]=par.get(mask,0.0)+coef
        targets[i]=par
    Minv={}
    for i in range(3):
        for combo in range(1,8):
            v=0
            for j in range(3):
                if combo>>j&1: v^=cols[j]
            if v==(1<<i): Minv[i]=combo
    req=[0x30 if side=='x' else 0x20]+[sum(1<<(6+j) for j in range(3) if Minv[i]>>j&1) for i in range(3)]
    allw=set(range(9))
    return dict(side=side,cols=cols,cond=cond,targets=targets,gates=[],fix=[],req=req,al=[allw]*4,newcode=newcode,depth=None,placed=False)
def dump(D,tag):
    pickle.dump(D,open(f'runs/{tag}.pkl','wb'))
    pl=[(m,i) for i in range(3) for m,a in D['targets'][i].items() if abs(a)>1e-12]
    open(f'runs/{tag}.lb','w').write('\n'.join([str(len(pl))]+[f'{m} {i}' for m,i in pl]+['4',' '.join(str(v) for v in D['req'])])+'\n')
    return {i:len([m for m,a in D['targets'][i].items() if abs(a)>1e-12]) for i in range(3)}
if __name__=="__main__":
    side=sys.argv[1]; cols=tuple(int(c) for c in sys.argv[2].split(',')); cs=sys.argv[3]; tag=sys.argv[4]
    cond={0:[],1:[],2:[]}
    if cs=='star': cond={0:[],1:[0],2:[0]}
    elif cs=='seq': cond={0:[],1:[0],2:[0,1]}
    elif cs=='seq2': cond={0:[],1:[0],2:[1]}
    D=makeD(side,cols,cond)
    sz=dump(D,tag)
    print(side,cols,cs,sz,'total',sum(sz.values()),flush=True)
