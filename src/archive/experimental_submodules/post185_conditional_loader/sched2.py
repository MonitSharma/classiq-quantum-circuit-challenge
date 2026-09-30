import random, itertools
from sched import gf2_inv_rows, TB, TMASK
NV=9
class LayerLoader:
    """layer-synchronous greedy parity-network scheduler for conditional loaders"""
    def __init__(self, targets, rng, w_setup=0.5, w_d2=0.3, noise=0.2, defer_rot=True, max_layers=400, w_dep=0.0):
        self.rem={i:dict(p) for i,p in targets.items()}
        dep={i:0 for i in range(3)}
        for i,p in targets.items():
            for m in p:
                for j in range(3):
                    if j!=i and m>>(6+j)&1: dep[j]+=1
        self.prio={i:1.0+w_dep*(1 if dep[i]>0 else 0) for i in range(3)}
        self.rng=rng; self.w_setup=w_setup; self.w_d2=w_d2; self.noise=noise; self.max_layers=max_layers
        self.rows=[1<<w for w in range(NV)]
        self.closed=set(); self.layers=[]  # list of layers: list of gates
        # layer 1: H on targets (fused later with rotation on const parity)
        self.gates=[]; 
        for i in range(3): self.gates.append((('h',),6+i))
        self.pending_u=set([6,7,8])  # wires whose last gate is single-qubit in the current open layer
    def open_bits(self): return sum(TB[i] for i in range(3) if i not in self.closed)
    def allowed(self):
        cl=sum(TB[i] for i in self.closed); out={}
        for i,p in self.rem.items():
            if i in self.closed: continue
            for m,a in p.items():
                if (m & TMASK & ~TB[i]) & ~cl: continue
                out[m]=(i,a)
        return out
    def snapshot(self, depth):
        return (depth, list(self.rows), {i:dict(p) for i,p in self.rem.items()}, set(self.closed), list(self.gates))
    def restore(self, snap):
        depth, rows, rem, closed, gates = snap
        self.rows=list(rows); self.rem={i:dict(p) for i,p in rem.items()}; self.closed=set(closed); self.gates=list(gates)
        return depth
    def run(self, start=None, record=False):
        self.snaps=[]
        if start is None:
            depth=1  # H layer
            al=self.allowed()
            for w in (6,7,8):
                r=self.rows[w]
                if r in al:
                    i,a=al[r]; self.gates.append((('rz',a),w)); del self.rem[i][r]
        else:
            depth=self.restore(start)
        while True:
            if record: self.snaps.append(self.snapshot(depth))
            # closings (fused as u3 on the wire, costs a layer slot) - treat as rotation-like single-qubit op this layer
            if len(self.closed)==3: break
            if depth>self.max_layers: return None
            depth+=1
            busy=set(); ops=[]
            al=self.allowed(); ob=self.open_bits()
            # closings
            for i in range(3):
                if i in self.closed or self.rem[i]: continue
                ws=[w for w in range(NV) if self.rows[w]&TB[i]]
                if len(ws)==1 and not (self.rows[ws[0]] & ob & ~TB[i]):
                    w=ws[0]; ops.append((('h',),w)); busy.add(w); self.closed.add(i); self.rows[w]=TB[i]
            al=self.allowed(); ob=self.open_bits()
            rotw=[w for w in range(NV) if w not in busy and self.rows[w] in al]
            coord=gf2_inv_rows(self.rows)
            pcs=[(m,coord(m),self.prio[al[m][0]]) for m in al]
            fin=[i for i in range(3) if i not in self.closed and not self.rem[i]]
            # candidate CX scoring
            def cx_score(c,t):
                new=self.rows[t]^self.rows[c]
                if bin(new&ob).count('1')>1: return None
                s=0.0; hit=new in al
                if hit: s+=10*self.prio[al[new][0]]
                for i in fin:
                    if self.rows[t]&TB[i] and not new&TB[i]: s+=8
                    if new&TB[i] and not self.rows[t]&TB[i]: return None
                d1=d2=0
                for m,C,pr in pcs:
                    if C>>t&1:
                        pc=bin(C).count('1'); pc2=pc+(-1 if C>>c&1 else 1)
                        if pc2==2 and pc!=2: d1+=pr
                        if pc==2 and pc2!=2: d1-=pr
                        if pc2==3 and pc!=3: d2+=pr
                        if pc==3 and pc2!=3: d2-=pr
                s+=self.w_setup*d1+self.w_d2*d2
                return s+self.noise*self.rng.random(), hit
            # decide: rotating wires are busy unless we prefer them as controls; simple: rotate
            for w in rotw:
                i,a=al[self.rows[w]]; ops.append((('rz',a),w)); busy.add(w); del self.rem[i][self.rows[w]]
            al=self.allowed()
            # greedy matching
            free=[w for w in range(NV) if w not in busy]
            cands=[]
            for c in free:
                for t in free:
                    if c==t: continue
                    sc=cx_score(c,t)
                    if sc is None: continue
                    cands.append((sc[0],sc[1],c,t))
            cands.sort(reverse=True)
            used=set(); chosen=[]
            for s,hit,c,t in cands:
                if c in used or t in used: continue
                if s<=0.05: break
                chosen.append((c,t)); used.add(c); used.add(t)
            for c,t in chosen:
                ops.append((('cx',),c,t))
            # apply cx updates simultaneously (disjoint)
            for c,t in chosen:
                self.rows[t]^=self.rows[c]
            if not ops:
                # stuck: force best setup move
                if not cands: return None
                s,hit,c,t=cands[0]; ops.append((('cx',),c,t)); self.rows[t]^=self.rows[c]
            self.gates.extend(ops)
        return depth
def best2(targets, restarts=100, seed=0):
    rng=random.Random(seed); best=None
    for r in range(restarts):
        p=dict(w_setup=rng.choice([0.2,0.5,1.0,2.0]), w_d2=rng.choice([0,0.1,0.3,0.6]), noise=rng.choice([0.05,0.3,1.0,3.0]))
        L=LayerLoader(targets, random.Random(rng.random()), **p)
        d=L.run()
        if d is None: continue
        from depth import gate_depth
        dd=gate_depth(L.gates)
        cxn=sum(1 for g in L.gates if g[0][0]=='cx')
        if best is None or (dd,cxn)<best[:2]: best=(dd,cxn,L,p)
    return best
