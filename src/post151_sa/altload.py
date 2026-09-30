"""Alternative synthesis L2 of a loader L1 with IDENTICAL phase terms and IDENTICAL final rows on all 9 wires,
so that inverse(L2) is a valid unloader for L1.  Usage: altload.py side src caps iters seed [lam mu]"""
import pickle, sys, os, subprocess, numpy as np
sys.path.insert(0,'.')
from lbeval2 import load_beam
from sim import check_loader2, symbolic_final
from kdrv import profile
import build
R='../../artifacts/118/recipes/'
BASE={'x':'x_loader_d44','y':'y_loader_d46_blkw'}
def l1_gates(side, src):
    D0=pickle.load(open(R+BASE[side]+'.pkl','rb'))
    if src=='champ': return D0, D0['gates']
    from lbeval2 import sa4
    bd,seq=load_beam(src); d,pen,g=sa4(D0,seq,tag='al1',binary='./c/sa4'); assert pen==0; return D0,g
def sim9(g):
    out=[]
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
def same_unitary(g1,g2):
    A=sim9(g1); B=sim9(g2); ov=np.sum(np.conj(A)*B,axis=1); ph=ov/abs(ov)
    return float(np.max(abs(abs(ov)-1))), float(np.max(abs(ph-ph[0])))
def run_sa(D, init, rows, caps, iters, seed, lam=4, mu=0.03, T0=0.5, T1=0.02, extra_env=None, tag='alt'):
    targets=D['targets']; plist=[(m,i,a) for i in range(3) for m,a in targets[i].items()]
    lines=[str(len(plist))]+[f"{m} {i}" for m,i,a in plist]
    lines+= [str(9)]+[f"{rows[w]} {1<<w}" for w in range(9)]
    lines+= ["0"]+[str(len(init))]+[f"{c} {t}" for c,t in init]
    out=f"runs/{tag}_{seed}.txt"; env=dict(os.environ); env['CAPS']=','.join(map(str,caps))
    if extra_env: env.update(extra_env)
    r=subprocess.run(['./c/sa4',str(seed),str(iters),str(T0),str(T1),str(lam),str(mu),out],input="\n".join(lines)+"\n",capture_output=True,text=True,env=env)
    txt=open(out).read().split("\n"); d,pen,L=map(int,txt[0].split()); gates=[]
    for line in txt[1:]:
        if not line: continue
        t=line.split()
        if t[0]=='H': gates.append((('h',),int(t[1])))
        elif t[0]=='R': gates.append((('rz',plist[int(t[2])][2]),int(t[1])))
        else: gates.append((('cx',),int(t[1]),int(t[2])))
    return d,pen,gates
if __name__=='__main__':
    side,src=sys.argv[1],sys.argv[2]; caps=list(map(int,sys.argv[3].split(','))); iters=int(sys.argv[4]); seed=int(sys.argv[5])
    lam=float(sys.argv[6]) if len(sys.argv)>6 else 4; mu=float(sys.argv[7]) if len(sys.argv)>7 else 0.03
    D,g1=l1_gates(side,src); rows=symbolic_final(g1); e1,_=profile(g1)
    init=[(g[1],g[2]) for g in g1 if g[0][0]=='cx']
    d,pen,g2=run_sa(D,init,rows,caps,iters,seed,lam,mu,tag=f'alt{side}')
    e2,_=profile(g2)
    print('L1 prof',e1,'rows',rows); print('L2 prof',e2,'pen',pen,'depth',d,'ncx',sum(1 for x in g2 if x[0][0]=='cx'))
    if pen==0:
        print('rows equal',symbolic_final(g2)==rows,'check',check_loader2(g2,D['newcode'])['max_dev'])
        print('unitary diff (|ov|-1, phase)',same_unitary(g1,g2))
        pickle.dump({'L1':g1,'L2':g2,'D':D},open(f'runs/alt_{side}_{seed}.pkl','wb'))
