import numpy as np, math, sys
from qa import parse
from build import u3m
from codes import *
from logo import logo_pixel
def kernel_action(path):
    n,g=parse(path)
    ops=[]
    for x in g:
        if x[0]=='cx': ops.append(('cx',x[1][0],x[1][1]))
        else: ops.append(('u',x[1][0],u3m(*[float(eval(a.replace('pi','math.pi'))) for a in x[2].split(',')])))
    res={}
    for b in range(256):
        psi=np.zeros(256,complex); psi[b]=1
        for o in ops:
            if o[0]=='cx':
                c,t=o[1],o[2]; idx=np.arange(256); sel=((idx>>c)&1)==1; lo=idx[sel & (((idx>>t)&1)==0)]; hi=lo|(1<<t)
                tmp=psi[lo].copy(); psi[lo]=psi[hi]; psi[hi]=tmp
            else:
                w=o[1]; U=o[2]; v=psi.reshape(-1,2,1<<w); a0=v[:,0,:].copy(); a1=v[:,1,:].copy()
                v[:,0,:]=U[0,0]*a0+U[0,1]*a1; v[:,1,:]=U[1,0]*a0+U[1,1]*a1
        k=int(np.argmax(abs(psi))); res[b]=(k,psi[k],abs(psi[k]))
    return res
if __name__=="__main__":
    res=kernel_action(sys.argv[1])
    print("min |amp|",min(r[2] for r in res.values()))
    # derive wire permutation: output bit j = input bit perm[j]
    perm={}
    for j in range(8):
        for i in range(8):
            if all(((res[b][0]>>j)&1)==((b>>i)&1) for b in range(256)): perm[j]=i
    print("output wire j carries input bit:",perm)
    # check phase on reachable codes: code bits [py,Ly0,Ly1,Ly2,px,Lx0,Lx1,Lx2]
    ph=[]; 
    for x in range(64):
        for y in range(64):
            cx_=(bin(x&48).count('1')%2); cy_=(y>>5)&1
            b = cy_ | (ycode[y]<<1) | (cx_<<4) | (xcode[x]<<5)
            ph.append(np.angle(res[b][1]) - (math.pi if logo_pixel(x,y) else 0))
    ph=np.array(ph); d=np.angle(np.exp(1j*(ph-ph[0])))
    print("kernel phase consistency (max dev from const):",np.max(np.abs(d)))
