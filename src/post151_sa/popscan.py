import pickle, sys, glob, os, time, json, numpy as np
sys.path.insert(0, '.')
from lbeval2 import load_beam, sa4
from sim import check_loader2, symbolic_final
from kdrv import profile, full_gates
from kgen import side_plan, span_map
R='../../artifacts/118/recipes/'
BASE={'x':pickle.load(open(R+'x_loader_d44.pkl','rb')),'y':pickle.load(open(R+'y_loader_d46_blkw.pkl','rb'))}
def sim9(g):
    """simulate a 9-qubit loader gate list on all 64 basis inputs (anc 6,7,8 = 0); return 64x512 states"""
    from kdrv import CO
    import build
    n=9; out=[]
    for x in range(64):
        psi=np.zeros(512,complex); psi[x]=1
        for gg in g:
            if gg[0][0]=='cx':
                c,t=gg[1],gg[2]; idx=np.arange(512); m=((idx>>c)&1)==1
                j=idx[m]; lo=j[((j>>t)&1)==0]; hi=lo|(1<<t); tmp=psi[lo].copy(); psi[lo]=psi[hi]; psi[hi]=tmp
            else:
                U=build.gate_matrix(gg[0]); w=gg[1]; v=psi.reshape(-1,2,1<<w); a0=v[:,0,:].copy(); a1=v[:,1,:].copy()
                v[:,0,:]=U[0,0]*a0+U[0,1]*a1; v[:,1,:]=U[1,0]*a0+U[1,1]*a1
        out.append(psi)
    return np.array(out)
res=[]
files=sys.argv[1:]
for p in files:
    try:
        bd, seq = load_beam(p)
        if not seq: continue
    except Exception as e: continue
    for side in ('x','y'):
        D=BASE[side]
        try:
            d, pen, g = sa4(D, seq, tag='ps', binary='./c/sa4')
        except Exception as e: continue
        if pen!=0: continue
        chk=check_loader2(g, D['newcode'])
        if chk['max_dev']>1e-9: continue
        e,_=profile(g); rows=symbolic_final(g)
        S=sim9(g)
        # canonical: basis index of each output and phase
        idx=np.argmax(abs(S),axis=1); ph=np.angle(S[np.arange(64),idx]); ph=ph-ph[0]
        key=(tuple(int(i) for i in idx), tuple(np.round(np.mod(ph,2*np.pi),6)))
        res.append({'file':os.path.basename(p),'side':side,'prof':e,'rows':rows,'maxabs':float(abs(S[np.arange(64),idx]).min()),'key':hash(key),'idx':[int(i) for i in idx],'ph':[float(v) for v in np.mod(ph,2*np.pi)]})
        print(os.path.basename(p),side,'prof',e,'rows',rows,'minamp %.3f'%res[-1]['maxabs'],'key',res[-1]['key']%100000,flush=True)
        break
pickle.dump(res,open('runs/popscan_%d.pkl'%os.getpid(),'wb'))
