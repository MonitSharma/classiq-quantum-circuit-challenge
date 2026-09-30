"""Exact MILP: minimise number of late-coordinate phase terms (then total) over reachable-code freedom."""
import sys, os, numpy as np, math, time
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
os.environ.setdefault('CLASS_CODES','/work/classiq/artifacts/185/class_codes.json'); os.environ.setdefault('CLASSIQ_ROOT','/work/classiq')
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix
from kgenco import build_F, CH
F,known=build_F(); U=np.where(~known)[0]; R=np.where(known)[0]
ST=[2,8,1,4,32,64,192,16]
coord={}
for s in range(256):
    v=0
    for k in range(8):
        if s>>k&1: v^=ST[k]
    coord[v]=s
LATEW=[0,0,0,float(os.environ.get('WLy1','1')),0,float(os.environ.get('WLx1','1')),float(os.environ.get('Wx12','1')),float(os.environ.get('Wpx','1'))]
def wt(m):
    s=coord[m]; w=max([LATEW[k] for k in range(8) if s>>k&1]+[0])
    return w
PI=math.pi
co=np.load(os.environ.get('CO0','/work/classiq/artifacts/116/recipes/kernel_co.npy'))
XU=CH[:,U]/256.0; nu=len(U); N=255   # masks 1..255
base=co/PI
EPS=float(os.environ.get('EPS','0.01'))
# vars: u (nu, free), n (N, int), z (N, binary)
nv=nu+2*N
c=np.zeros(nv)
for j,m in enumerate(range(1,256)): c[nu+N+j]=wt(m)+EPS
A=lil_matrix((2*N,nv)); lb=[]; ub=[]
for j,m in enumerate(range(1,256)):
    # frac = base[m] + XU[m]u - n ; -0.5 z <= frac <= 0.5 z
    for r,sg in ((2*j,1),(2*j+1,-1)):
        A[r,:nu]=sg*XU[m]; A[r,nu+j]=-sg; A[r,nu+N+j]=-0.5
        lb.append(-np.inf); ub.append(-sg*base[m])
A=csr_matrix(A)
integ=np.r_[np.zeros(nu),np.ones(2*N)]
lo=np.r_[np.full(nu,-64.0),np.full(N,-64.0),np.zeros(N)]; hi=np.r_[np.full(nu,64.0),np.full(N,64.0),np.ones(N)]
t0=time.time()
res=milp(c=c,constraints=LinearConstraint(A,lb,ub),integrality=integ,bounds=Bounds(lo,hi),options={'time_limit':float(os.environ.get('TL','600')),'disp':False,'mip_rel_gap':0})
print('status',res.status,res.message,'%.0fs'%(time.time()-t0))
if res.x is not None:
    u=res.x[:nu]; cc=(base+XU@u); fr=cc-np.round(cc); fr[0]=0; fr[np.abs(fr)<1e-7]=0
    nz=[m for m in range(1,256) if abs(fr[m])>1e-7]
    late=[m for m in nz if wt(m)>0]
    print('terms',len(nz),'late',len(late),'obj',res.fun)
    ph0=CH.T@co; ph1=CH.T@(fr*PI); d=(ph1-ph0)[R]; d=d-d[0]; d=(d+PI)%(2*PI)-PI; print('check',np.max(np.abs(d)))
    out=os.environ.get('OUT','/work/k/late/milp.npy'); np.save(out,fr*PI); print('saved',out)
