import pickle, sys, collections
sys.path.insert(0,'.')
from kdrv import full_gates, profile, KTERMS, CO, code_vectors
from sim import symbolic_final

R='../../artifacts/118/recipes/'
DX=pickle.load(open(R+'x_loader_d44.pkl','rb')); DY=pickle.load(open(R+'y_loader_d46_blkw.pkl','rb'))
pl,kg=pickle.load(open(R+'kernel_plan_and_gates_118.pkl','rb'))
seq,W,ST,rdy,unl=pl
print('W   ',W); print('ST  ',ST); print('rdy ',rdy); print('unl ',unl)
for nm,D in (('x',DX),('y',DY)):
    g=full_gates(D); r=symbolic_final(g); e,l=profile(g)
    print(nm,'req',D.get('req'),'depth',max(e),'e',e,'rows',r)
print('codevecs',code_vectors(DX,DY))
# kernel body
rot=collections.Counter(); cxc=collections.Counter(); cxt=collections.Counter()
ncx=0
for g in kg[1:]:
    if g[0]=='C': ncx+=1; cxc[g[1]]+=1; cxt[g[2]]+=1
    else: rot[g[1]]+=1
print('kernel CX total',ncx,'rot total',sum(rot.values()))
print('per kernel-wire (local idx): rot, cxctrl, cxtgt')
for i in range(18):
    if rot[i] or cxc[i] or cxt[i]:
        print('  w%2d  rot %3d  ctrl %3d  tgt %3d  rdy %3d  ST %4d' % (i,rot[i],cxc[i],cxt[i],rdy[i],ST[i]))
# mask-popcount histogram
pc=collections.Counter(bin(m).count('1') for m in KTERMS)
print('mask popcount hist',sorted(pc.items()))
