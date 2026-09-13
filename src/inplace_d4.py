"""y-side: 2 in-place code wires whose update functions depend on only 4 wires.
   t1 ^= g1(t2, f_S)   |S|=3   -> 16 rotations
   t2 ^= g2(t1', f_T)  |T|=3   -> 16 rotations
Need <=4 classes per block (2 ancilla bits separate them)."""
import sys, itertools, json, time; sys.path.insert(0,'src')
from collections import Counter
from z3 import Bool, Solver, Implies, PbLe, sat, And, Not, Xor, If
import two_stage_oracle as ts

def subspaces2():
    seen=set(); out=[]
    for a,b in itertools.combinations(range(1,64),2):
        S={0,a,b,a^b}
        if len(S)!=4: continue
        k=frozenset(S)
        if k in seen: continue
        seen.add(k); out.append((sorted(S),(a,b)))
    return out
def basis(gen):
    full=list(gen)
    for m in range(1,64):
        t=full+[m]; piv={}; ok=True
        for v in t:
            x=v
            while x:
                i=x.bit_length()-1
                if i in piv: x^=piv[i]
                else: piv[i]=x;break
            else: ok=False;break
        if ok and len(full)<6: full.append(m)
        if len(full)==6: break
    piv={}
    for j,row in enumerate(full):
        comb=1<<j;r=row
        while r:
            i=r.bit_length()-1
            if i in piv:
                a,c=piv[i];r^=a;comb^=c
            else: piv[i]=(r,comb);break
    def C(y):
        v=y;o=0
        while v:
            i=v.bit_length()-1
            a,c=piv[i];v^=a;o^=c
        return o
    return C,full
def trial(cls,gen,S,T,timeout=6000):
    C,full=basis(list(gen))
    grid=[[None]*4 for _ in range(16)]
    for y in range(64):
        c=C(y); grid[(c>>2)&15][c&3]=cls[y]
    classes=sorted(set(cls))
    G1={}; G2={}
    for s in range(8):
        for v in range(2): G1[(s,v)]=Bool(f'g1_{s}_{v}')
    for t in range(8):
        for v in range(2): G2[(t,v)]=Bool(f'g2_{t}_{v}')
    U=[[Bool(f'u{b}_{c}') for c in range(len(classes))] for b in range(4)]
    So=Solver(); So.set('timeout',timeout)
    for f in range(16):
        s=sum(((f>>S[i])&1)<<i for i in range(3))
        t_=sum(((f>>T[i])&1)<<i for i in range(3))
        for tt in range(4):
            a=(tt&1)==1; b=((tt>>1)&1)==1
            a2=Xor(If(b,G1[(s,1)],G1[(s,0)]), a)
            b2=Xor(If(a2,G2[(t_,1)],G2[(t_,0)]), b)
            ci=classes.index(grid[f][tt])
            for bv in range(4):
                cond=[a2 if bv&1 else Not(a2), b2 if bv&2 else Not(b2)]
                So.add(Implies(And(*cond),U[bv][ci]))
    for b in range(4): So.add(PbLe([(U[b][i],1) for i in range(len(classes))],4))
    if So.check()==sat:
        m=So.model()
        return {'basis':full,'S':list(S),'T':list(T),
                'g1':{f'{s},{v}':bool(m[G1[(s,v)]]) for s in range(8) for v in range(2)},
                'g2':{f'{t},{v}':bool(m[G2[(t,v)]]) for t in range(8) for v in range(2)},
                'blocks':[[classes[i] for i in range(len(classes)) if m[U[b][i]]] for b in range(4)]}
    return None
W2=subspaces2()
cls=ts.ROWCLS; tot=Counter(cls); cands=[]
for W,gen in W2:
    seen=set(); rows=[]
    for y in range(64):
        if y in seen: continue
        co=[y^w for w in W]; seen.update(co); rows.append(co)
    need=sum(max(max(sum(1 for t in r if cls[t]==c) for r in rows), -(-n//16)) for c,n in tot.items())
    if need<=16: cands.append((need,gen))
cands.sort()
print(f'y: {len(cands)} candidates',flush=True)
subs=list(itertools.combinations(range(4),3))
got=None; t0=time.time()
for need,gen in cands:
    if time.time()-t0>250: break
    for Sx in subs:
        for Tx in subs:
            r=trial(cls,gen,Sx,Tx)
            if r: got=(gen,r); break
        if got: break
    if got: break
print(f'y: {"SAT gen="+str(got[0])+" S="+str(got[1]["S"])+" T="+str(got[1]["T"]) if got else "no d=4 solution in budget"} ({time.time()-t0:.0f}s)',flush=True)
if got:
    print('   blocks=',got[1]['blocks'])
    json.dump(got[1],open(sys.argv[1],'w'))
