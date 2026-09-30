import random, math
NZ=6; NT=3; NV=9
TB=[1<<(6+i) for i in range(3)]
TMASK=sum(TB)
def gf2_inv_rows(rows):
    # rows: list of NV ints (basis). returns function coord(p) -> int bitmask over wires
    n=len(rows)
    # build augmented: we want coefficients c such that XOR_{w in c} rows[w] = p
    # Gaussian elimination to get pivot structure
    basis=[]  # list of (vec, combo)
    piv={}
    for w,r in enumerate(rows):
        v=r; c=1<<w
        for b in sorted(piv.keys(),reverse=True):
            if v>>b &1:
                pv,pc=piv[b]; v^=pv; c^=pc
        assert v!=0
        b=v.bit_length()-1
        # reduce existing pivots? keep simple (upper-triangular elimination on the fly)
        piv[b]=(v,c)
    def coord(p):
        v=p; c=0
        for b in sorted(piv.keys(),reverse=True):
            if v>>b &1:
                pv,pc=piv[b]; v^=pv; c^=pc
        assert v==0
        return c
    return coord

class Loader:
    def __init__(self, targets, rng, w_time=1.0, w_hit=3.0, w_pot=0.6, w_d2=0.15, noise=0.3, max_steps=3000):
        # targets: dict i -> dict mask->angle ; masks include bit 6+i and conditioning bits
        self.rem={i:dict(p) for i,p in targets.items()}
        self.rng=rng; self.w=(w_time,w_hit,w_pot,w_d2,noise); self.max_steps=max_steps
        self.rows=[1<<w for w in range(NV)]
        self.closed=set()
        self.gates=[]
        self.wt=[0]*NV; self.lastu=[False]*NV
        for i in range(3):
            self.u3(6+i,('h',))
    def u3(self,w,g):
        if not self.lastu[w]:
            self.wt[w]+=1; self.lastu[w]=True
        self.gates.append((g,w))
    def cx(self,c,t):
        tm=max(self.wt[c],self.wt[t])+1
        self.wt[c]=self.wt[t]=tm; self.lastu[c]=self.lastu[t]=False
        self.rows[t]^=self.rows[c]
        self.gates.append((('cx',),c,t))
    def open_bits(self):
        return sum(TB[i] for i in range(3) if i not in self.closed)
    def allowed(self):
        cl=sum(TB[i] for i in self.closed)
        out={}
        for i,p in self.rem.items():
            if i in self.closed: continue
            for m,a in p.items():
                others=m & TMASK & ~TB[i]
                if others & ~cl: continue
                out[m]=(i,a)
        return out
    def do_rotations(self):
        al=self.allowed()
        did=False
        for w in range(NV):
            r=self.rows[w]
            if r in al:
                i,a=al[r]
                self.u3(w,('rz',a))
                del self.rem[i][r]
                del al[r]
                did=True
        return did
    def try_close(self):
        did=False
        for i in range(3):
            if i in self.closed or self.rem[i]: continue
            ws=[w for w in range(NV) if self.rows[w]&TB[i]]
            if len(ws)==1:
                w=ws[0]
                if self.rows[w] & self.open_bits() & ~TB[i]: continue
                self.u3(w,('h',))
                self.closed.add(i)
                self.rows[w]=TB[i]  # after closing, wire holds L_i
                did=True
        return did
    def done(self):
        return len(self.closed)==3
    def depth(self):
        return max(self.wt)
    def step(self):
        w_time,w_hit,w_pot,w_d2,noise=self.w
        al=self.allowed()
        ob=self.open_bits()
        coord=gf2_inv_rows(self.rows)
        # remaining allowed parities coordinates
        cand=[]
        tmin=min(max(self.wt[c],self.wt[t]) for c in range(NV) for t in range(NV) if c!=t)
        fin=[i for i in range(3) if i not in self.closed and not self.rem[i]]
        pcs=[(m,coord(m)) for m in al]
        for c in range(NV):
            for t in range(NV):
                if c==t: continue
                new=self.rows[t]^self.rows[c]
                nob=bin(new & ob).count('1')
                if nob>1: continue
                # don't pollute wire with bit of a finished-but-unclosed target
                score=0.0
                if new in al: score+=w_hit
                for i in fin:
                    if self.rows[t]&TB[i] and not new&TB[i]: score+=w_hit*0.8
                    if new&TB[i] and not self.rows[t]&TB[i]: score-=w_hit
                # potential: change in distances. coordinate change: new basis = rows with t replaced.
                # coord'(p): if coord(p) has bit t -> coord(p) ^ bit c toggled? rows'[t]=rows[t]^rows[c]
                # p = sum_{w in C} rows[w]; rows[t] = rows'[t]^rows[c] => if t in C: C' = C ^ {c}
                d1=0; d2=0; base1=0; base2=0
                for m,C in pcs:
                    pc=bin(C).count('1')
                    if C>>t &1: pc2=bin(C ^ (1<<c)).count('1')
                    else: pc2=pc
                    if pc==2: base1+=1
                    if pc==3: base2+=1
                    if pc2==2: d1+=1
                    if pc2==3: d2+=1
                score+=w_pot*(d1-base1)+w_d2*(d2-base2)
                tm=max(self.wt[c],self.wt[t])
                score-=w_time*(tm-tmin)
                score+=noise*self.rng.random()
                cand.append((score,c,t))
        cand.sort(reverse=True)
        s,c,t=cand[0]
        self.cx(c,t)
    def run(self):
        steps=0
        while not self.done():
            self.do_rotations(); self.try_close()
            if self.done(): break
            self.step(); steps+=1
            if steps>self.max_steps: return None
        return self.depth()

def best_schedule(targets, restarts=50, seed=0, **kw):
    best=None
    rng=random.Random(seed)
    for r in range(restarts):
        params=dict(w_time=rng.choice([0.5,1,2,3]), w_hit=rng.choice([2,3,5]), w_pot=rng.choice([0.3,0.6,1.0]),
                    w_d2=rng.choice([0.0,0.1,0.3]), noise=rng.choice([0.1,0.5,1.0]))
        params.update(kw)
        L=Loader(targets, random.Random(rng.random()), **params)
        d=L.run()
        if d is None: continue
        cxn=sum(1 for g in L.gates if g[0][0]=='cx')
        if best is None or (d,cxn)<(best[0],best[1]): best=(d,cxn,L,params)
    return best
