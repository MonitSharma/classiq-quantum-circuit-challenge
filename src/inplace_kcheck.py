import sys, json, math, random, itertools, time; sys.path.insert(0,'src')
import numpy as np, two_stage_oracle as ts

def basis_fn(full):
    piv={}
    for j,row in enumerate(full):
        comb=1<<j; r=row
        while r:
            i=r.bit_length()-1
            if i in piv:
                a,c=piv[i]; r^=a; comb^=c
            else: piv[i]=(r,comb); break
    def C(y):
        v=y;o=0
        while v:
            i=v.bit_length()-1
            a,c=piv[i]; v^=a; o^=c
        return o
    return C

dy=json.load(open(sys.argv[1]))       # y: d=4 family
dx=json.load(open(sys.argv[2]))['x']  # x: shift family

Cy=basis_fn(dy['basis']); S=dy['S']; T=dy['T']
g1={tuple(map(int,k.split(','))):v for k,v in dy['g1'].items()}
g2={tuple(map(int,k.split(','))):v for k,v in dy['g2'].items()}
def yblock(y):
    c=Cy(y); t=c&3; f=(c>>2)&15
    a=t&1; b=(t>>1)&1
    s=sum(((f>>S[i])&1)<<i for i in range(3))
    tt=sum(((f>>T[i])&1)<<i for i in range(3))
    a2=a ^ int(g1[(s,b)])
    b2=b ^ int(g2[(tt,a2)])
    return a2|(b2<<1)
Cx=basis_fn(dx['basis']); sh=dx['shifts']
def xblock(x):
    c=Cx(x); t=c&3; f=(c>>2)&15
    return t ^ sh[f]

ycell={}; xcell={}
for y in range(64): ycell.setdefault((yblock(y),ts.ROWCLS[y]),[]).append(y)
for x in range(64): xcell.setdefault((xblock(x),ts.COLCLS[x]),[]).append(x)
print('y cells',len(ycell),'x cells',len(xcell))
from collections import Counter
print('  y per block',sorted(Counter(k[0] for k in ycell).values()),
      ' x per block',sorted(Counter(k[0] for k in xcell).values()))

def walsh256(a):
    a=np.array(a,float); h=1
    while h<256:
        for i in range(0,256,2*h):
            lo=a[i:i+h].copy(); hi=a[i+h:i+2*h].copy()
            a[i:i+h]=lo+hi; a[i+h:i+2*h]=lo-hi
        h*=2
    return a/256
def build(yl,xl):
    tab=np.zeros(256)
    for yk,ym in ycell.items():
        yv=yk[0]|(yl[yk]<<2)
        for xk,xm in xcell.items():
            xv=xk[0]|(xl[xk]<<2)
            tab[yv|(xv<<4)]=math.pi*(1 if ts.logo(xm[0],ym[0]) else 0)
    return tab
def legal(cells,rng):
    lab={}; bg={}
    for k in cells: bg.setdefault(k[0],[]).append(k)
    for g,ks in bg.items():
        for k,o in zip(ks,rng.sample(range(4),len(ks))): lab[k]=o
    return lab,bg
rng=random.Random(5)
yl,ybg=legal(ycell,rng); xl,xbg=legal(xcell,rng)
K=int(np.sum(np.abs(walsh256(build(yl,xl)))>1e-9)); best=K; bl=(dict(yl),dict(xl))
t0=time.time()
while time.time()-t0<120:
    side=rng.random()<0.5
    lab,bg=(yl,ybg) if side else (xl,xbg)
    new=dict(lab); g=rng.choice(list(bg)); ks=bg[g]
    if len(ks)>1 and rng.random()<0.5:
        a,b=rng.sample(ks,2); new[a],new[b]=new[b],new[a]
    else:
        k=rng.choice(ks); used={new[j] for j in ks if j!=k}
        fr=[v for v in range(4) if v not in used]
        if not fr: continue
        new[k]=rng.choice(fr)
    nK=int(np.sum(np.abs(walsh256(build(new,xl) if side else build(yl,new)))>1e-9))
    if nK<=best:
        best=nK
        if side: yl=new
        else: xl=new
print(f'kernel Walsh support K = {best}  (current 224 design: 117)')
load=2*(320/6.0); kern=best/3.0
print(f'FLOOR: loader {load:.0f} + kernel {kern:.0f} = {load+kern:.0f}   (current design floor 187)')
print(f'realistic at the observed 1.17x synthesis ratio: {(load+kern)*1.17:.0f}')
