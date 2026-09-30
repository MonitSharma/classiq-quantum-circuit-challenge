"""Anneal labels for the 5-bit code (2 free parities + 3-bit label of 5 vars)
minimising the integer-ANF kernel cost on 10 wires."""
import math, random, sys, json, pickle
from post185_qcorr_oracle import logo, par
R={};ROW=[0]*64;C={};COL=[0]*64
for y in range(64): ROW[y]=R.setdefault(tuple(int(logo(x,y)) for x in range(64)),len(R))
for x in range(64): COL[x]=C.setdefault(tuple(int(logo(x,y)) for y in range(64)),len(C))
N=10
ORDER=sorted(range(1<<N),key=lambda m:(m.bit_count(),m))
COSTW=[0,0.05,0.5,1,4,12,30,80,200,500,1000]
EV=[sum(1<<i for i,m in enumerate(ORDER) if m&~w==0) for w in range(1<<N)]

def frame(cls,pairs):
    """returns cell[x]=(a,b,v) and sig groups: key (b,sig)"""
    V=list(range(16)); p,q,u,w=pairs
    cell={}
    for r,a,b in ((p,0,0),(q,1,0),(u,0,1),(w,1,1)):
        for v in V: cell[r^v]=(a,b,v)
    sig={}
    for x in range(64):
        a,b,v=cell[x]
        r0,r1=((p,q) if b==0 else (u,w))
        sig[x]=(b,(cls[r0^v],cls[r1^v]))
    return cell,sig

XC,XS=frame(COL,(0,55,16,39)); YC,YS=frame(ROW,(0,16,32,48))
XK=sorted(set(XS.values())); YK=sorted(set(YS.values()))
def codes(cell,sig,lab):
    return [cell[x][0]|(cell[x][1]<<1)|(lab[sig[x]]<<2) for x in range(64)]
PAIRS=None
def poly(xc,yc):
    piv={}; seen={}
    for x in range(64):
        for y in range(64):
            w=yc[y]|(xc[x]<<5); v=int(logo(x,y))
            if w in seen:
                if seen[w]!=v: return None
                continue
            seen[w]=v
            row=EV[w]; rhs=v
            while row:
                i=(row&-row).bit_length()-1
                if i in piv: a,b=piv[i]; row^=a; rhs^=b
                else: piv[i]=(row,rhs); break
            if not row and rhs: return None
    sol=0
    for i in sorted(piv,reverse=True):
        row,rhs=piv[i]
        if ((row&sol).bit_count()&1)^rhs: sol|=1<<i
    return sol
def cost(sol): return sum(COSTW[ORDER[i].bit_count()] for i in range(1<<N) if sol>>i&1)

def init(keys):
    lab={}
    for b in (0,1):
        ks=[k for k in keys if k[0]==b]
        vals=random.sample(range(8),len(ks))
        for k,v in zip(ks,vals): lab[k]=v
    return lab
def main(steps,seed):
    random.seed(seed)
    xl=init(XK); yl=init(YK)
    sol=poly(codes(XC,XS,xl),codes(YC,YS,yl)); cur=cost(sol); best=(cur,dict(xl),dict(yl),sol)
    for st in range(steps):
        lab,keys=(xl,XK) if random.random()<0.5 else (yl,YK)
        k=random.choice(keys); val=random.randrange(8)
        other=next((o for o in keys if o[0]==k[0] and lab[o]==val and o!=k),None)
        prev=lab[k]; lab[k]=val
        if other: lab[other]=prev
        s=poly(codes(XC,XS,xl),codes(YC,YS,yl))
        c=cost(s) if s is not None else 1e9
        T=2+20*(1-st/steps)
        if c<=cur or random.random()<math.exp((cur-c)/T):
            cur=c; sol=s
            if c<best[0]:
                best=(c,dict(xl),dict(yl),s)
                terms=[ORDER[i] for i in range(1<<N) if s>>i&1]
                print(st,"cost",round(c,2),"terms",len(terms),flush=True)
        else:
            lab[k]=prev
            if other: lab[other]=val
    terms=[ORDER[i] for i in range(1<<N) if best[3]>>i&1]
    hist={}
    for t in terms: hist[t.bit_count()]=hist.get(t.bit_count(),0)+1
    print("FINAL cost",best[0],"terms",len(terms),"deg hist",sorted(hist.items()),flush=True)
    pickle.dump(dict(xl=best[1],yl=best[2],terms=terms),open(f'/tmp/scratch/k10_{seed}.pkl','wb'))
if __name__=='__main__': main(int(sys.argv[1]),int(sys.argv[2]))
