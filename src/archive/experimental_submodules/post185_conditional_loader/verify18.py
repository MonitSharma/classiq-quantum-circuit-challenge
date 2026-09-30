import numpy as np, re, math, sys, hashlib, time
from logo import logo_pixel
from build import u3m
N=18
def parse_full(path):
    src=open(path).read()
    st=[s.strip() for s in re.sub(r"//[^\n]*","",src).split(";") if s.strip()]
    assert st[0]=="OPENQASM 2.0" and st[1]=='include "qelib1.inc"'
    assert re.fullmatch(r"qreg\s+q\s*\[\s*18\s*\]",st[2])
    gates=[]
    for s in st[3:]:
        m=re.fullmatch(r"u3\s*\(([^,]+),([^,]+),([^,]+)\)\s+q\s*\[\s*(\d+)\s*\]",s)
        if m:
            par=[float(eval(m.group(k).replace('pi','math.pi'))) for k in (1,2,3)]
            gates.append(('u',int(m.group(4)),u3m(*par))); continue
        m=re.fullmatch(r"cx\s+q\s*\[\s*(\d+)\s*\]\s*,\s*q\s*\[\s*(\d+)\s*\]",s)
        if m: gates.append(('cx',int(m.group(1)),int(m.group(2)))); continue
        raise ValueError(s)
    return gates,src
def simulate(gates, psi):
    psi=psi.copy()
    idx=np.arange(1<<N)
    for g in gates:
        if g[0]=='cx':
            c,t=g[1],g[2]
            sel=((idx>>c)&1)==1
            a=idx[sel]; b=a^(1<<t)
            # swap amplitudes of pairs where control=1: each pair once
            lo=a[((a>>t)&1)==0]; hi=lo|(1<<t)
            tmp=psi[lo].copy(); psi[lo]=psi[hi]; psi[hi]=tmp
        else:
            w=g[1]; U=g[2]
            v=psi.reshape(-1,2,1<<w)
            a0=v[:,0,:].copy(); a1=v[:,1,:].copy()
            v[:,0,:]=U[0,0]*a0+U[0,1]*a1
            v[:,1,:]=U[1,0]*a0+U[1,1]*a1
    return psi
if __name__=="__main__":
    path=sys.argv[1]; nstates=int(sys.argv[2]) if len(sys.argv)>2 else 3
    gates,src=parse_full(path)
    print("sha256",hashlib.sha256(src.encode()).hexdigest())
    target=np.array([[(-1 if logo_pixel(x,y) else 1) for x in range(64)] for y in range(64)],dtype=complex) # [y][x]
    rng=np.random.default_rng(12345)
    worst=0; worst_leak=0
    for k in range(nstates):
        t0=time.time()
        ph=np.exp(1j*rng.uniform(-np.pi,np.pi,size=4096))  # fully random phase per basis input (not product)
        psi=np.zeros(1<<N,complex)
        xy=np.arange(4096)   # index bits: x in bits 0..5, y in bits 6..11
        psi[xy]=ph/64
        out=simulate(gates,psi)
        want=np.array([ph[i]/64*target[i>>6][i&63] for i in range(4096)])
        ov=np.vdot(want,out[xy]); g=ov/abs(ov)
        err=np.max(np.abs(out[xy]-g*want))
        leak=np.sqrt(max(0.0,1-np.sum(np.abs(out[xy])**2)))
        worst=max(worst,err); worst_leak=max(worst_leak,leak)
        print(f"state {k}: max amp error {err:.2e} (relative {err*64:.2e}), leakage {leak:.2e}, |overlap| {abs(ov):.12f}, t {time.time()-t0:.1f}s",flush=True)
    print("PASS" if worst*64<1e-8 and worst_leak<1e-6 else "FAIL", worst*64, worst_leak)
