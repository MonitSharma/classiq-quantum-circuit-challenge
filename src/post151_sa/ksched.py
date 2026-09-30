import pickle, sys, collections
sys.path.insert(0,'.')
from kdrv import KTERMS, CO
R='../../artifacts/118/recipes/'
pl,kg=pickle.load(open(R+'kernel_plan_and_gates_118.pkl','rb'))
seq,W,ST,rdy,unl=pl
wt=[None]*18; l=[False]*18
# replay crit2 style
e=[43,35,44,44,42,42,42,44,40,35,45,39,45,44,44,43,46,45]
wt=list(e); lu=[False]*18
ev=[]
for g in kg[1:]:
    if g[0]=='C':
        c,t=g[1],g[2]; tau=max(wt[c],wt[t])+1; wt[c]=wt[t]=tau; lu[c]=lu[t]=False
        ev.append((tau,'CX',c,t))
    else:
        w=g[1]
        if not lu[w]: wt[w]+=1; lu[w]=True
        ev.append((wt[w],'R',w,round((g[2]/6.283185307179586*2)%4,2)))
ev.sort(key=lambda x:x[0])
busy=collections.defaultdict(list)
for tau,k,*rest in ev: busy[tau].append((k,)+tuple(rest))
print('layer  ops                                  busy-wires')
for tau in range(min(busy), 77):
    ops=busy.get(tau,[])
    ws=sorted(set(v for o in ops for v in o[1:]))
    print('%5d  %-36s %s' % (tau, ' '.join(('%s%d-%d'%(o[0],o[1],o[2]) if o[0]=='CX' else 'R%d'%o[1]) for o in ops), ws))
