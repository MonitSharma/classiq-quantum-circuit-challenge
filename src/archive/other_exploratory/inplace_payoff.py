"""Rebuild the two 14-cell 'simultaneous' constructions, anneal K, project depth."""
import sys, itertools, json, math, random, time; sys.path.insert(0,'src')
import numpy as np, two_stage_oracle as ts
def perm_of(M,c):
    p=[]
    for t in range(4):
        a,b=t&1,(t>>1)&1
        p.append(((M[0][0]*a^M[0][1]*b^c[0])&1)|((((M[1][0]*a^M[1][1]*b^c[1])&1))<<1))
    return tuple(p)
I=[[1,0],[0,1]]; U=[[1,1],[0,1]]; L=[[1,0],[1,1]]
SIM=sorted({perm_of(M,c) for M in (I,U,L) for c in itertools.product([0,1],repeat=2)})
def basisfn_gen(gen):
    full=list(gen)
    for m in range(1,64):
        t=full+[m]; piv={}; ok=True
        for v in t:
            x=v
            while x:
                i=x.bit_length()-1
                if i in piv: x^=piv[i]
                else: piv[i]=x; break
            else: ok=False; break
        if ok and len(full)<6: full.append(m)
        if len(full)==6: break
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
    return C,full
def solve(cls,gen,cap):
    C,full=basisfn_gen(gen)
    grid=[[None]*4 for _ in range(16)]
    for t in range(64):
        c=C(t); grid[(c>>2)&15][c&3]=cls[t]
    blocks=[set() for _ in range(4)]; sol=[None]*16; bud=[3000000]
    def cells(): return sum(len(b) for b in blocks)
    def rec(f):
        bud[0]-=1
        if bud[0]<0: raise TimeoutError
        if f==16: return cells()<=cap
        for p in SIM:
            added=[]; ok=True
            for t in range(4):
                b=p[t]; c=grid[f][t]
                if c not in blocks[b]:
                    if len(blocks[b])>=4: ok=False; break
                    blocks[b].add(c); added.append((b,c))
            if ok and cells()<=cap:
                sol[f]=p
                if rec(f+1): return True
            for b,c in added: blocks[b].discard(c)
        return False
    if rec(0): return C,full,list(sol),[sorted(b) for b in blocks],cells()
    return None
ry=solve(ts.ROWCLS,(17,32),14); rx=solve(ts.COLCLS,(23,32),14)
print(f'y: cells={ry[4]} blocks={ry[3]}')
print(f'x: cells={rx[4]} blocks={rx[3]}',flush=True)
Cy,fy,py,_,_=ry; Cx,fx,px,_,_=rx
def yblk(t): c=Cy(t); return py[(c>>2)&15][c&3]
def xblk(t): c=Cx(t); return px[(c>>2)&15][c&3]
yc={}; xc={}
for t in range(64): yc.setdefault((yblk(t),ts.ROWCLS[t]),[]).append(t)
for t in range(64): xc.setdefault((xblk(t),ts.COLCLS[t]),[]).append(t)
print(f'reachable kernel entries {len(yc)}x{len(xc)}={len(yc)*len(xc)} of 256 '
      f'-> {256-len(yc)*len(xc)} don\'t-cares  (your build: 182/74)',flush=True)
def walsh256(a):
    a=np.array(a,float); h=1
    while h<256:
        for i in range(0,256,2*h):
            lo=a[i:i+h].copy(); hi=a[i+h:i+2*h].copy()
            a[i:i+h]=lo+hi; a[i+h:i+2*h]=lo-hi
        h*=2
    return a/256
rng=random.Random(int(sys.argv[2]) if len(sys.argv)>2 else 17)
def legal(c):
    lab={}; bg={}
    for k in c: bg.setdefault(k[0],[]).append(k)
    for g,ks in bg.items():
        for k,o in zip(ks,rng.sample(range(4),len(ks))): lab[k]=o
    return lab,bg
def build(yl,xl,dc):
    tab=np.zeros(256); seen=set()
    for yk,ym in yc.items():
        yv=yk[0]|(yl[yk]<<2)
        for xk,xm in xc.items():
            i=yv|((xk[0]|(xl[xk]<<2))<<4); seen.add(i)
            tab[i]=math.pi*(1 if ts.logo(xm[0],ym[0]) else 0)
    for i in range(256):
        if i not in seen and dc.get(i,0): tab[i]=math.pi
    return tab,seen
best=None; t0=time.time()
while time.time()-t0<620:
    yl,ybg=legal(yc); xl,xbg=legal(xc); dc={}
    tab,_=build(yl,xl,dc); cur=int(np.sum(np.abs(walsh256(tab))>1e-9)); T=8.0
    for it in range(9000):
        r=rng.random(); nyl,nxl,ndc=yl,xl,dc
        if r<0.4:
            new=dict(yl); g=rng.choice(list(ybg)); ks=ybg[g]
            if len(ks)>1 and rng.random()<0.5:
                a,b=rng.sample(ks,2); new[a],new[b]=new[b],new[a]
            else:
                k=rng.choice(ks); used={new[j] for j in ks if j!=k}
                fr=[v for v in range(4) if v not in used]
                if not fr: continue
                new[k]=rng.choice(fr)
            nyl=new
        elif r<0.8:
            new=dict(xl); g=rng.choice(list(xbg)); ks=xbg[g]
            if len(ks)>1 and rng.random()<0.5:
                a,b=rng.sample(ks,2); new[a],new[b]=new[b],new[a]
            else:
                k=rng.choice(ks); used={new[j] for j in ks if j!=k}
                fr=[v for v in range(4) if v not in used]
                if not fr: continue
                new[k]=rng.choice(fr)
            nxl=new
        else:
            _,s=build(yl,xl,{}); fr=[i for i in range(256) if i not in s]
            if not fr: continue
            new=dict(dc); i=rng.choice(fr); new[i]=1-new.get(i,0); ndc=new
        t2,_=build(nyl,nxl,ndc); nK=int(np.sum(np.abs(walsh256(t2))>1e-9))
        if nK<=cur or rng.random()<math.exp(-(nK-cur)/max(T,0.4)):
            yl,xl,dc,cur=nyl,nxl,ndc,nK
            if best is None or nK<best[0]:
                best=(nK,dict(yl),dict(xl),dict(dc))
                print(f'   K={nK}',flush=True)
        T*=0.99985
K=best[0]
def st(r): return r/2.95+4
enc=st(48)+st(128); cur_enc=st(192)
print(f'\nannealed K = {K}   (your build: K=117 at rate 2)')
print(f'encoding {enc:.0f}/block (2 stages: 48 rot in-place + 128 rot load) vs yours {cur_enc:.0f}')
print(f'kernel {K/3*1.05:.0f} (rate 3, two ancillas freed) vs yours {117/2*1.05:.0f}')
model=2*enc+K/3*1.05; curmodel=2*cur_enc+117/2*1.05
print(f'MODEL total {model:.0f}  vs your architecture model {curmodel:.0f} (actual 190)')
print(f'PROJECTED depth = {model*190/curmodel:.0f}')
json.dump({'K':K,'ygen':[17,32],'xgen':[23,32],'ybasis':fy,'xbasis':fx,
           'yperms':[list(p) for p in py],'xperms':[list(p) for p in px],
           'ylab':{f'{k[0]},{k[1]}':v for k,v in best[1].items()},
           'xlab':{f'{k[0]},{k[1]}':v for k,v in best[2].items()},
           'dontcare':{str(k):v for k,v in best[3].items() if v},
           'ycells':len(yc),'xcells':len(xc)},open(sys.argv[1],'w'))
