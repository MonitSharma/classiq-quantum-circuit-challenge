import pickle, sys
from kdrv import assemble, full_gates, KTERMS, CO
from sim import symbolic_final
def layers_of(path):
    L=open(path).read().split('\n'); d,tau0=map(int,L[0].split()); lay=[]
    for l in L[1:d+1]:
        t=list(map(int,l.split())); lay.append([(t[1+2*q],t[2+2*q]) for q in range(t[0])])
    return lay,tau0
def build_kg(fixpath,beampath):
    fx=pickle.load(open(fixpath,'rb')); seq,W,rdy=fx[0],fx[1],fx[2]
    lay,tau0=layers_of(beampath)
    kg=[('S',list(range(18)))]
    for c,t in seq: kg.append(('C',c,t))
    T=set(KTERMS); idx={m:k for k,m in enumerate(KTERMS)}
    rows=[1<<i for i in range(8)]; done=set(); pend={}
    for i in range(8):
        if rows[i] in T:
            done.add(rows[i]); pend[i]=rows[i]
    for k,layer in enumerate(lay,1):
        tau=tau0+k
        used={x for p in layer for x in p}
        for i in list(pend):
            if i not in used and tau>rdy[i]: kg.append(('R',W[i],2*CO[pend.pop(i)]))
        for c,t in layer:
            assert t not in pend
            kg.append(('C',W[c],W[t]))
        new=[]
        for c,t in layer: new.append((t,rows[t]^rows[c]))
        for t,v in new:
            rows[t]=v
            if v in T and v not in done: done.add(v); pend[t]=v
    for i,v in pend.items(): kg.append(('R',W[i],2*CO[v]))
    assert rows==[1<<i for i in range(8)] and done==T, (rows, len(done))
    for c,t in reversed(seq): kg.append(('C',c,t))
    return kg
if __name__=="__main__":
    xp,yp,fixp,bp,out=sys.argv[1:6]
    DX=pickle.load(open(xp,'rb')); DY=pickle.load(open(yp,'rb'))
    kg=build_kg(fixp,bp); print(out,assemble(DX,DY,kg,out)); pickle.dump(kg,open(out.replace('.qasm','_kernel.pkl'),'wb'))
