import pickle, sys, collections
sys.path.insert(0,'.')
from kdrv import KTERMS, CO
R='../../artifacts/118/recipes/'
pl,kg=pickle.load(open(R+'kernel_plan_and_gates_118.pkl','rb'))
seq,W,ST,rdy,unl=pl
rot=collections.Counter(); cxc=collections.Counter(); cxt=collections.Counter()
for g in kg[1:]:
    if g[0]=='C': cxc[g[1]]+=1; cxt[g[2]]+=1
    else: rot[g[1]]+=1
print('code wires (model idx): ', W)
print('  idx side rot ctrl tgt touches  rdy  |  T=118 DDL slack  |  T=117 DDL slack')
tot=0
for k,i in enumerate(W):
    tc=rot[i]+cxc[i]+cxt[i]; tot+=tc
    d118=118-unl[k]; d117=117-unl[k]
    print('  %3d %3s %3d %4d %3d %6d %5d  |  %5d %5d       |  %5d %5d' % (
        i, 'y' if i>=9 else 'x', rot[i], cxc[i], cxt[i], tc, rdy[k], d118, d118-rdy[k]-tc, d117, d117-rdy[k]-tc))
print('total touches on code wires', tot, 'CX', sum(cxc.values())+sum(cxt.values()), 'rot', sum(rot.values()))
print('non-code wires touched:', {i:(rot[i],cxc[i],cxt[i]) for i in range(18) if i not in W and (rot[i] or cxc[i] or cxt[i])})
pc=collections.Counter(bin(m).count('1') for m in KTERMS)
print('mask popcount hist', sorted(pc.items()))
