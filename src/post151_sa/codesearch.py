"""Explore alternative class-label assignments and their loader-support profile."""
import numpy as np, itertools, random, sys
from logo import logo_pixel
# column/row classes
def classes():
    rows, rowcls = {}, [0]*64
    for y in range(64):
        rowcls[y] = rows.setdefault(tuple(1 if logo_pixel(x,y) else 0 for x in range(64)), len(rows))
    cols, colcls = {}, [0]*64
    for x in range(64):
        colcls[x] = cols.setdefault(tuple(1 if logo_pixel(x,y) else 0 for y in range(64)), len(cols))
    return rowcls, colcls
ROWCLS, COLCLS = classes()
H=np.array([[1]])
for _ in range(6): H=np.block([[H,H],[H,-H]])
def support(f):
    """#nonzero Walsh coefficients of f (0/1 vector of length 64)"""
    c=H@f.astype(float)
    return int(np.sum(np.abs(c)>1e-9))-0
def side_data(side):
    if side=='x':
        par=[bin(v&48).count('1')%2 for v in range(64)]; cls=COLCLS
    else:
        par=[bin(v&32).count('1')%2 for v in range(64)]; cls=ROWCLS
    groups={}
    for v in range(64):
        groups.setdefault((par[v],cls[v]),[]).append(v)
    keys=sorted(groups)
    return groups, keys, par, cls
def eval_assignment(groups, keys, assign):
    """assign: dict key->3-bit label; returns supports of the 7 frame combos"""
    bits=np.zeros((3,64),int)
    for k,lab in assign.items():
        for v in groups[k]:
            for j in range(3):
                bits[j][v]=(lab>>j)&1
    sups={}
    for c in range(1,8):
        f=np.zeros(64,int)
        for j in range(3):
            if c>>j&1: f^=bits[j]
        sups[c]=support(f)
    return sups,bits
def random_assign(keys,rng):
    # per parity: injective map of that parity's classes into 0..7
    byp={0:[k for k in keys if k[0]==0],1:[k for k in keys if k[0]==1]}
    assign={}
    for p in (0,1):
        labs=rng.sample(range(8),len(byp[p]))
        for k,l in zip(byp[p],labs): assign[k]=l
    return assign
if __name__=='__main__':
    side=sys.argv[1]; n=int(sys.argv[2]); seed=int(sys.argv[3])
    groups,keys,par,cls=side_data(side)
    print(side,'groups',len(keys),'per parity',[sum(1 for k in keys if k[0]==p) for p in (0,1)])
    rng=random.Random(seed)
    best=[]
    for it in range(n):
        a=random_assign(keys,rng)
        sups,_=eval_assignment(groups,keys,a)
        m=min(sups.values())
        best.append((m,sorted(sups.values()),a))
    best.sort(key=lambda t:t[0])
    print('best min-support:',best[0][0],'sorted supports',best[0][1])
    print('median min-support:',best[len(best)//2][0])
    import pickle; pickle.dump(best[:20],open(f'runs/cs_{side}_{seed}.pkl','wb'))
