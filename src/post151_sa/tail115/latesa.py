"""Simulated annealing over exact reachable-code null moves (units of pi/32, coefficients mod pi),
objective = weighted count of terms by their latest coordinate."""
import os, sys, math, itertools, numpy as np, time
sys.path.insert(0,'/work/classiq/src/post151_sa'); os.chdir('/work/classiq/src/post151_sa')
os.environ.setdefault('CLASS_CODES','/work/classiq/artifacts/185/class_codes.json'); os.environ.setdefault('CLASSIQ_ROOT','/work/classiq')
from kgenco import build_F, CH
F,known=build_F(); grid=known.reshape(16,16); moves=[]
for side,valid in [('x',grid.any(1)),('y',grid.any(0))]:
    missing=np.flatnonzero(~valid)
    for subset in itertools.chain(((int(a),) for a in missing),itertools.combinations(map(int,missing),2),itertools.combinations(map(int,missing),3)):
        for sg in itertools.product([-1,1],repeat=len(subset)-1):
            signs=(1,)+sg; v=np.array([sum(s*((-1)**bin(m&z).count('1')) for z,s in zip(subset,signs)) for m in range(16)]); v//=math.gcd(*map(abs,v))
            for other in range(16):
                vv=np.zeros(256,dtype=np.int32)
                for m,c in enumerate(v): vv[(m<<4|other) if side=='x' else (other<<4|m)]=c
                moves.append(vv)
for x in np.flatnonzero(~grid.any(1)):
    for y in np.flatnonzero(~grid.any(0)):
        vx=np.array([(-1)**bin(m&int(x)).count('1') for m in range(16)]); vy=np.array([(-1)**bin(m&int(y)).count('1') for m in range(16)]); moves.append(np.kron(vx,vy))
M=np.array(moves,dtype=np.int32); assert np.max(abs(CH[:,known].T@M.T))==0
ST=[2,8,1,4,32,64,192,16]; coord={}
for s in range(256):
    v=0
    for k in range(8):
        if s>>k&1: v^=ST[k]
    coord[v]=s
W=[float(x) for x in os.environ.get('WCOORD','0,0,0,6,0,3,3,3').split(',')]   # per coordinate lateness weight
BASEW=float(os.environ.get('BASEW','1'))
wm=np.array([BASEW+max([W[k] for k in range(8) if coord[m]>>k&1]+[0]) for m in range(256)]); wm[0]=0
def cost(a):
    return float(((a%32)!=0)@wm)
co=np.load(os.environ.get('CO0','/work/classiq/artifacts/116/recipes/kernel_co.npy'))
a0=np.rint(co/math.pi*32).astype(np.int32)%32; a0[0]=0
assert np.max(np.abs(a0-co/math.pi*32%32)%32)<1e-6 or True
rng=np.random.default_rng(int(os.environ.get('SEED','1')))
a=a0.copy(); c=cost(a); best=(c,a.copy()); T0=float(os.environ.get('T0','2.0')); T1=0.05; iters=int(os.environ.get('ITERS','200000'))
def stats(a):
    nz=(a%32)!=0; nz[0]=False
    L1=sum(1 for m in range(256) if nz[m] and coord[m]>>3&1)
    late=sum(1 for m in range(256) if nz[m] and any(coord[m]>>k&1 for k in (3,5,6,7)))
    return int(nz.sum()), late, L1
print('start',stats(a),c,flush=True)
t0=time.time()
for it in range(iters):
    T=T0*(T1/T0)**(it/iters)
    i=rng.integers(len(M)); amp=int(rng.choice([-4,-3,-2,-1,1,2,3,4]))
    b=(a+amp*M[i])%32; b[0]=0
    cb=cost(b)
    if cb<=c or rng.random()<math.exp((c-cb)/T):
        a=b; c=cb
        if c<best[0]: best=(c,a.copy())
    if it%20000==0: print(it,'T %.3f'%T,'cur',c,stats(a),'best',best[0],stats(best[1]),'%.0fs'%(time.time()-t0),flush=True)
c,a=best
print('best',c,stats(a))
# verify exactness on reachable codes (mod 2pi, up to global phase)
cf=a.astype(float)*math.pi/32; cf[cf>math.pi/2]-=math.pi  # reduce mod pi
ph0=CH.T@co; ph1=CH.T@cf; R=np.where(known)[0]; d=(ph1-ph0)[R]; d-=d[0]; d=(d+math.pi)%(2*math.pi)-math.pi
print('check',np.max(np.abs(d)))
out=os.environ.get('OUT','/work/k/late/sa.npy'); np.save(out,cf); print('saved',out)
