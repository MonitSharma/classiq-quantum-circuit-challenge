import pickle, sys
from kdrv import *
DX=pickle.load(open(sys.argv[1],'rb')); DY=pickle.load(open(sys.argv[2],'rb')); kg=pickle.load(open(sys.argv[3],'rb'))
gx=full_gates(DX); gy=full_gates(DY)
ex,lx=profile(gx); ey,ly=profile(gy); e=ex+ey; lu=lx+ly
sigma=kg[0][1]; wt=list(e); l=list(lu); first=[None]*18; ncx=[0]*18
for g in kg[1:]:
    if g[0]=='C':
        c,t=g[1],g[2]
        for w in (c,t):
            if first[w] is None: first[w]=max(wt[c],wt[t])
            ncx[w]+=1
        tau=max(wt[c],wt[t])+1; wt[c]=wt[t]=tau; l[c]=l[t]=False
    else:
        w=g[1]
        if not l[w]: wt[w]+=1; l[w]=True
T=0
for w in range(18):
    u=sigma[w]; tot=wt[w]+e[u]-(1 if (l[w] and lu[u]) else 0); T=max(T,tot)
    print(w,'xy'[w>=9],'load',e[w],'kfirst',first[w],'kend',wt[w],'ncx',ncx[w],'unload',e[u],'total',tot)
print('T',T)
