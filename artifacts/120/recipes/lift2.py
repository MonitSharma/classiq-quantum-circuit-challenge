import numpy as np, sys, random, pickle
from codes import H, bits, xcode, ycode
from z64 import Sys
def lift_target(L, seeds=40, verbose=False):
    n=(H@L.astype(np.int64)); assert np.all(n%2==0)
    p=(n//2)%64
    v=0
    for x in range(64):
        if L[x]: v^=x
    best=None
    for e in (0,1):
        Tfull=[S for S in range(64) if (bin(S&v).count('1')%2)==e]
        for sd in range(seeds):
            rng=random.Random(1000*e+sd)
            order=Tfull[:]; rng.shuffle(order)
            S_=Sys(64)
            kept=[]
            for Sx in order:
                a=[1 if bin(Sx&x).count('1')%2==0 else -1 for x in range(64)]
                if S_.add(a,(-int(p[Sx]))%64): kept.append(Sx)
            w=S_.solve()
            if w is None: continue
            w=np.array(w,dtype=np.int64)
            m=(H@w)
            R=(p+m)%64
            gates=int(np.count_nonzero(R))
            if best is None or gates<best[0]: best=(gates,w.copy(),len(kept),e)
    return best
def coeffs(L,w):
    n=(H@L.astype(np.int64)); m=H@w
    a=np.pi*(n+2*m)/64.0
    a=np.remainder(a+np.pi,2*np.pi)-np.pi
    return a
if __name__=='__main__':
    side=sys.argv[1]; combos=[int(c) for c in sys.argv[2].split(',')]; seeds=int(sys.argv[3])
    code=xcode if side=='x' else ycode; B=bits(code)
    for combo in combos:
        L=np.zeros(64,dtype=np.int64)
        for j in range(3):
            if combo>>j&1: L^=B[j]
        base=int(np.count_nonzero(H@L))
        g,w,k,e=lift_target(L,seeds)
        a=coeffs(L,w)
        nz=int(np.sum(np.abs(a)>1e-9))
        # check correctness: sum a_s chi_s(x) == pi L(x) mod 2pi
        rec=H@a
        err=np.max(np.abs(np.remainder(rec-np.pi*L+np.pi,2*np.pi)-np.pi))
        print(f"{side} combo {combo}: exact {base} -> lifted {nz} (kept {k}, e={e}) err {err:.2e}",flush=True)
        np.save(f'runs/liftw_{side}_{combo}.npy',w)
