"""For sampled (x,y) label assignments: loader first-bit supports and an estimate of kernel terms."""
import numpy as np, random, sys, pickle
from codesearch import side_data, eval_assignment, random_assign, H
from logo import logo_pixel
from scipy.optimize import linprog
from scipy.sparse import csr_matrix
chi=np.array([[(-1.0)**bin(m&c).count('1') for c in range(256)] for m in range(256)])
def kernel_terms_estimate(xassign, yassign, gx, kx, gy, ky, rounds=8):
    # build code for each x,y
    xcode=[0]*64; ycode=[0]*64
    gxs,keysx,parx,clsx=gx; gys,keysy,pary,clsy=gy
    for k,lab in xassign.items():
        for v in gxs[k]: xcode[v]=lab
    for k,lab in yassign.items():
        for v in gys[k]: ycode[v]=lab
    M=-np.ones(256)
    for x in range(64):
        px=parx[x]
        for y in range(64):
            py=pary[y]
            c=py | (ycode[y]<<1) | (px<<4) | (xcode[x]<<5)
            v=1 if logo_pixel(x,y) else 0
            if M[c]>=0 and M[c]!=v: return None
            M[c]=v
    R=[c for c in range(256) if M[c]>=0]; U=[c for c in range(256) if M[c]<0]
    r0=(chi[:,R]@M[R])/256.0; XU=chi[:,U]/256.0
    u=np.zeros(len(U)); w=np.ones(256); w[0]=0; best=None
    for it in range(rounds):
        base=r0+XU@u; n=np.round(base)
        nu=XU.shape[1]
        c=np.zeros(nu+256); c[nu:]=w
        A=np.hstack([XU,-np.eye(256)]); B=np.hstack([-XU,-np.eye(256)])
        Am=csr_matrix(np.vstack([A,B])); bm=np.concatenate([-(base-n),(base-n)])
        res=linprog(c,A_ub=Am,b_ub=bm,bounds=[(None,None)]*nu+[(0,None)]*256,method='highs')
        if not res.success: break
        u=u+res.x[:nu]
        b=r0+XU@u; d=b[1:]-np.round(b[1:]); k=int(np.sum(np.abs(d)>1e-7))
        if best is None or k<best: best=k
        w=1.0/(np.abs(np.concatenate([[0],d]))+1e-3); w[0]=0
    return best
if __name__=='__main__':
    n=int(sys.argv[1]); seed=int(sys.argv[2]); thresh=int(sys.argv[3]) if len(sys.argv)>3 else 99
    gx=side_data('x'); gy=side_data('y')
    rng=random.Random(seed); out=[]
    for it in range(n):
        ax=random_assign(gx[1],rng); ay=random_assign(gy[1],rng)
        sx,_=eval_assignment(gx[0],gx[1],ax); sy,_=eval_assignment(gy[0],gy[1],ay)
        mx=min(sx.values()); my=min(sy.values())
        if mx>thresh or my>thresh: continue
        kt=kernel_terms_estimate(ax,ay,gx,None,gy,None)
        print('x first',mx,'y first',my,'kernel est',kt,flush=True)
        out.append((mx,my,kt,ax,ay))
    pickle.dump(out,open(f'runs/ck_{seed}.pkl','wb'))
