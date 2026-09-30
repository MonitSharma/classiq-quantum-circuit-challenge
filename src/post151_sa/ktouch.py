import pickle, sys, collections
sys.path.insert(0,'.')
pl,kg=pickle.load(open(sys.argv[1],'rb'))
seq,W,ST,rdy,unl=pl
rot=collections.Counter(); cxc=collections.Counter(); cxt=collections.Counter()
for g in kg[1:]:
    if g[0]=='C': cxc[g[1]]+=1; cxt[g[2]]+=1
    else: rot[g[1]]+=1
print('W',W); print('rdy',rdy); print('unl',unl)
print('wire  rdy  rot ctrl tgt touches  2*rdy+touches   cap@117')
bad=0
for k,w in enumerate(W):
    tc=rot[w]+cxc[w]+cxt[w]; v=2*rdy[k]+tc
    if v>117: bad+=1
    print('w%2d   %2d  %3d %4d %3d %6d   %4d          %4d%s'%(w,rdy[k],rot[w],cxc[w],cxt[w],tc,v,117-rdy[k],'  OVER' if v>117 else ''))
print('wires over 117:',bad,' cx',sum(1 for g in kg[1:] if g[0]=='C'))
