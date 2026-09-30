import pickle, sys
sys.path.insert(0,'.')
R='../../artifacts/118/recipes/'
pl,kg=pickle.load(open(R+'kernel_plan_and_gates_118.pkl','rb'))
seq,W,ST,rdy,unl=pl
ex=[43,35,44,44,42,42,42,44,40]; ey=[35,45,39,45,44,44,43,46,45]
e=ex+ey
def sched(body):
    avail=list(e); last=list(e); lu=[False]*18
    for g in body:
        if g[0]=='C':
            c,t=g[1],g[2]; tau=max(avail[c],avail[t])+1
            avail[c]=avail[t]=tau; lu[c]=lu[t]=False; last[c]=last[t]=tau
        else:
            w=g[1]
            if lu[w]: tau=avail[w]
            else: tau=avail[w]+1
            avail[w]=tau; lu[w]=True; last[w]=tau
    return last
last=sched(kg[1:])
print('wire  rdy  e   asap-last  T118  cap@T117')
for k,w in enumerate(W):
    print('w%2d   %2d  %2d   %4d      %4d  %4d'%(w,rdy[k],e[w],last[w],last[w]+e[w],117-e[w]))
print('noncode last',[last[w] for w in range(18) if w not in W])
print('T =',max(last[w]+e[w] for w in range(18)))
