import sys, numpy as np
from postopt import parse_ops, fuse, depth, write
X=np.array([[0,1],[1,0]])
def kind(U):
    if abs(U[0,1])+abs(U[1,0])<1e-12: return 'Z'
    if np.max(abs(U@X-X@U))<1e-12: return 'X'
    return 'G'
def tag(o): return o if o[0]=='cx' else (o[0],o[1],o[2],kind(o[2]))
def com(a,b):
    sa=set(a[1]); sb=set(b[1])
    if not sa&sb: return True
    if a[0]=='cx' and b[0]=='cx': return a[1][0]!=b[1][1] and b[1][0]!=a[1][1]
    if a[0]!='cx' and b[0]!='cx':
        return a[3]==b[3] and a[3]!='G' or np.max(abs(a[2]@b[2]-b[2]@a[2]))<1e-12
    if a[0]!='cx': a,b=b,a
    w=b[1][0]
    if w==a[1][0]: return b[3]=='Z'
    return b[3]=='X'
def simplify(ops, verbose=True):
    ops=[tag(o) for o in ops]; ncx=nrz=0
    i=0
    while i<len(ops):
        a=ops[i]; hit=False
        for j in range(i+1,len(ops)):
            b=ops[j]
            if not set(a[1])&set(b[1]): continue
            if a[0]=='cx' and b[0]=='cx' and a[1]==b[1]:
                del ops[j]; del ops[i]; ncx+=1; hit=True; break
            if a[0]!='cx' and b[0]!='cx' and a[1]==b[1] and a[3]=='Z' and b[3]=='Z':
                U=b[2]@a[2]; ops[j]=('u3',b[1],U,'Z'); del ops[i]; nrz+=1; hit=True; break
            if not com(a,b): break
        if hit: i=max(0,i-1); continue
        i+=1
    if verbose: print('cancelled cx pairs',ncx,'merged diag 1q',nrz)
    return [o[:3] for o in ops]
if __name__=='__main__':
    ops=fuse(parse_ops(sys.argv[1])); print('before',len(ops),depth(ops))
    o2=fuse(simplify(ops)); print('after',len(o2),depth(o2),'cx',sum(1 for o in o2 if o[0]=='cx'))
    cnt=[0]*18
    for o in o2:
        for w in o[1]: cnt[w]+=1
    print(cnt)
    if len(sys.argv)>2: write(o2,sys.argv[2])
