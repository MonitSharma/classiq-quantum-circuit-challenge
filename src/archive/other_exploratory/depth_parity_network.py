"""Depth-aware parity network: greedy over whole CX layers."""
import random
import numpy as np
from qiskit import QuantumCircuit
from qiskit.synthesis.linear import synth_cnot_count_full_pmh

def walsh(vals):
    a=np.asarray(vals,float).copy(); h=1; n=len(a)
    while h<n:
        for i in range(0,n,2*h):
            lo=a[i:i+h].copy(); hi=a[i+h:i+2*h].copy()
            a[i:i+h]=lo+hi; a[i+h:i+2*h]=lo-hi
        h*=2
    return a/n

def restore(state, n):
    """CX circuit taking `state` back to the identity basis."""
    mat=np.array([[(state[w]>>j)&1 for j in range(n)] for w in range(n)],dtype=bool)
    inv=np.eye(n,dtype=bool); m=mat.copy()
    for c in range(n):
        p=next(r for r in range(c,n) if m[r][c])
        if p!=c:
            m[[c,p]]=m[[p,c]]; inv[[c,p]]=inv[[p,c]]
        for r in range(n):
            if r!=c and m[r][c]:
                m[r]^=m[c]; inv[r]^=inv[c]
    best=None
    for s in (1,2,3):
        q=synth_cnot_count_full_pmh(inv, section_size=s)
        if best is None or (q.depth(),q.size())<(best.depth(),best.size()): best=q
    return best


def _coords(target, state, n):
    """Subset of wire indices whose current states XOR to `target` (states are a basis)."""
    piv={}
    for w in range(n):
        row, comb = state[w], 1<<w
        while row:
            i=row.bit_length()-1
            if i in piv:
                r2,c2=piv[i]; row^=r2; comb^=c2
            else:
                piv[i]=(row,comb); break
    v, out = target, 0
    while v:
        i=v.bit_length()-1
        if i not in piv: return None
        r2,c2=piv[i]; v^=r2; out^=c2
    return [w for w in range(n) if out>>w & 1]

def synth(phase_values, n, seed=0, tol=1e-12):
    co=walsh(phase_values)
    targets={m:float(co[m]) for m in range(1,1<<n) if abs(co[m])>tol}
    rng=random.Random(seed)
    q=QuantumCircuit(n)
    state=[1<<w for w in range(n)]
    if abs(co[0])>tol: q.global_phase+=co[0]
    def flush():
        for w in range(n):
            m=state[w]
            if m in targets:
                q.rz(-2*targets.pop(m), w)
    flush()
    stall=0
    while targets:
        # score every ordered pair; pick a disjoint set maximising immediate hits
        cand=[]
        for a in range(n):
            for b in range(n):
                if a==b: continue
                nm=state[a]^state[b]
                gain=1 if nm in targets else 0
                # lookahead: how many targets one further CX away from nm
                la=sum(1 for c in range(n) if c!=b and (nm^state[c]) in targets)
                cand.append((gain*4+la,gain,rng.random(),a,b))
        cand.sort(reverse=True)
        used=set(); layer=[]
        for gain,la,_,a,b in cand:
            if a in used or b in used: continue
            if gain==0 and la==0 and layer: continue
            used.add(a); used.add(b); layer.append((a,b))
            if len(layer)==n//2: break
        before=len(targets)
        if not layer or stall>=6:
            # directed routing: drive one host straight onto a remaining parity
            m=min(targets)
            done=False
            for b in sorted(range(n), key=lambda w: bin(state[w]^m).count('1')):
                sub=_coords(m ^ state[b], state, n)
                if sub is None or b in sub: continue
                for a in sub:
                    q.cx(a,b); state[b]^=state[a]
                done=True; break
            if not done:
                a,b=rng.sample(range(n),2); q.cx(a,b); state[b]^=state[a]
            flush(); stall=0
            continue
        for a,b in layer:
            q.cx(a,b); state[b]^=state[a]
        flush()
        stall = 0 if len(targets)<before else stall+1
    assert not targets, f'{len(targets)} parities unreached'
    q.compose(restore(state,n), inplace=True)
    return q

if __name__=='__main__':
    import sys, json, itertools
    sys.path.insert(0,'src')
    import two_stage_oracle as ts
    labs=json.load(open(sys.argv[1]))
    ylab={tuple(map(int,k.split(','))):v for k,v in labs['ylab'].items()}
    xlab={tuple(map(int,k.split(','))):v for k,v in labs['xlab'].items()}
    tab=ts.kernel_table(ylab,xlab,fill=0.0)
    sup=int(np.sum(np.abs(ts.walsh8(tab))>1e-12))
    print('kernel walsh support',sup)
    from qiskit import transpile
    best=None
    for seed in range(int(sys.argv[2]) if len(sys.argv)>2 else 8):
        q=synth(list(tab),8,seed=seed)
        nat=transpile(q,basis_gates=['u3','cx'],optimization_level=3,
                      qubits_initially_zero=False,seed_transpiler=0)
        print(f'  seed {seed}: depth {nat.depth()} cx {nat.count_ops().get("cx",0)}',flush=True)
        if best is None or (nat.depth(),nat.size())<(best.depth(),best.size()): best=nat
    print('BEST kernel depth',best.depth(),'cx',best.count_ops().get('cx',0))
    from qiskit.quantum_info import Operator
    op=Operator(best).data
    d=np.diag(op); off=float(np.max(np.abs(op-np.diag(d))))
    want=np.exp(1j*np.array(tab)); r=d/want
    print('offdiag',off,'phase spread',float(np.max(np.abs(r-r[0]))))
