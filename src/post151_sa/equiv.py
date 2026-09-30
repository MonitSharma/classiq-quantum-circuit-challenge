import sys, numpy as np, hashlib
sys.path.insert(0,'.')
from verify18 import parse_full, simulate
def qdepth(g):
    wt=[0]*18
    for x in g:
        ws=(x[1],x[2]) if x[0]=='cx' else (x[1],)
        l=max(wt[w] for w in ws)+1
        for w in ws: wt[w]=l
    return max(wt)
ga,_=parse_full(sys.argv[1]); gb,src=parse_full(sys.argv[2])
rng=np.random.default_rng(int(sys.argv[3]) if len(sys.argv)>3 else 7)
ph=[]
for k in range(2):
    psi=rng.normal(size=1<<18)+1j*rng.normal(size=1<<18); psi/=np.linalg.norm(psi)
    a=simulate(ga,psi); b=simulate(gb,psi); ov=np.vdot(a,b); ph.append(ov)
    print('state',k,'|ov|=%.15f'%abs(ov),'maxdiff %.2e'%np.max(abs(b-a*ov/abs(ov))))
print('phase consistency %.2e'%abs(ph[0]/abs(ph[0])-ph[1]/abs(ph[1])))
print('B depth',qdepth(gb),'cx',sum(1 for x in gb if x[0]=='cx'),'u3',sum(1 for x in gb if x[0]!='cx'),'sha',hashlib.sha256(src.encode()).hexdigest()[:8])
