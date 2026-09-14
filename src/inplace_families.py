"""In-place families for the 2 block wires, in increasing cost.

t=(a,b) in {0,1}^2. Per row f we may apply any permutation from the family.
  a' = a ^ u0(f) ^ u1(f)*b        b' = b ^ v0(f) ^ v1(f)*a'   (triangular)
All 24 permutations of {0,1}^2 are affine (S_4 = AGL(2,2)).

  shift        u1=v1=0                  4 perms   32 rot  1 stage  (simultaneous)
  simultaneous u1*v1=0, b' uses ORIG a 12 perms   48 rot  ~1 stage (reversible iff u1v1=0)
  triangular   any u,v                 16 perms   64 rot  2 stages
  full         all affine              24 perms   needs a conditional swap
"""
import sys, itertools, json, time; sys.path.insert(0,'src')
import two_stage_oracle as ts

def mats():
    out=[]
    for m in itertools.product([0,1],repeat=4):
        M=[[m[0],m[1]],[m[2],m[3]]]
        if (M[0][0]*M[1][1]^M[0][1]*M[1][0])&1: out.append(M)
    return out
def perm_of(M,c):
    p=[]
    for t in range(4):
        a,b=t&1,(t>>1)&1
        a2=(M[0][0]*a^M[0][1]*b^c[0])&1
        b2=(M[1][0]*a^M[1][1]*b^c[1])&1
        p.append(a2|(b2<<1))
    return tuple(p)
ALLM=mats()
I=[[1,0],[0,1]]; U=[[1,1],[0,1]]; L=[[1,0],[1,1]]; Z=[[1,1],[1,0]]
FAMS={
 'shift':        [perm_of(I,c) for c in itertools.product([0,1],repeat=2)],
 'simultaneous': sorted({perm_of(M,c) for M in (I,U,L) for c in itertools.product([0,1],repeat=2)}),
 'triangular':   sorted({perm_of(M,c) for M in (I,U,L,Z) for c in itertools.product([0,1],repeat=2)}),
 'full':         sorted({perm_of(M,c) for M in ALLM for c in itertools.product([0,1],repeat=2)}),
}
COST={'shift':(32,1),'simultaneous':(48,1),'triangular':(64,2),'full':(96,3)}
for k,v in FAMS.items(): print(f'{k}: {len(v)} permutations, {COST[k][0]} rot, {COST[k][1]} stage(s)')

def sub2():
    seen=set(); out=[]
    for a,b in itertools.combinations(range(1,64),2):
        S=frozenset({0,a,b,a^b})
        if len(S)!=4 or S in seen: continue
        seen.add(S); out.append((a,b))
    return out
def basisfn(gen):
    full=list(gen)
    for m in range(1,64):
        t=full+[m]; piv={}; ok=True
        for v in t:
            x=v
            while x:
                i=x.bit_length()-1
                if i in piv: x^=piv[i]
                else: piv[i]=x; break
            else: ok=False; break
        if ok and len(full)<6: full.append(m)
        if len(full)==6: break
    piv={}
    for j,row in enumerate(full):
        comb=1<<j; r=row
        while r:
            i=r.bit_length()-1
            if i in piv:
                a,c=piv[i]; r^=a; comb^=c
            else: piv[i]=(r,comb); break
    def C(y):
        v=y;o=0
        while v:
            i=v.bit_length()-1
            a,c=piv[i]; v^=a; o^=c
        return o
    return C,full
def solve(cls,gen,fam,cap):
    C,full=basisfn(list(gen))
    grid=[[None]*4 for _ in range(16)]
    for t in range(64):
        c=C(t); grid[(c>>2)&15][c&3]=cls[t]
    blocks=[set() for _ in range(4)]; sol=[None]*16
    budget=[20000]
    def cells(): return sum(len(b) for b in blocks)
    def rec(f):
        budget[0]-=1
        if budget[0]<0: raise TimeoutError
        if f==16: return cells()<=cap
        for p in fam:
            added=[]; ok=True
            for t in range(4):
                b=p[t]; c=grid[f][t]
                if c not in blocks[b]:
                    if len(blocks[b])>=4: ok=False; break
                    blocks[b].add(c); added.append((b,c))
            if ok and cells()<=cap:
                sol[f]=p
                if rec(f+1): return True
            for b,c in added: blocks[b].discard(c)
        return False
    try:
        if rec(0): return list(sol),[sorted(b) for b in blocks],full,cells()
    except TimeoutError:
        return None
    return None
GENS=sub2()
out={}
for name,cls,target in (('y',ts.ROWCLS,14),('x',ts.COLCLS,13)):
    print(f'\n=== {name} (target <= {target} cells)',flush=True)
    for fam in ('shift','simultaneous','triangular','full'):
        best=None; t0=time.time()
        for cap in ([14,15,16] if name=='y' else [13,14,15,16]):
            for gen in GENS:
                if time.time()-t0>240: break
                r=solve(cls,gen,FAMS[fam],cap)
                if r: best=(cap,gen,r); break
            if best: break
        if best:
            cap,gen,(sol,blocks,full,n)=best
            rot,st=COST[fam]
            print(f'  {fam:13s} cells={n} gen={gen} ({rot} rot, {st} stage)  blocks={blocks}',flush=True)
            out.setdefault(name,{})[fam]={'gen':list(gen),'basis':full,
                'perms':[list(p) for p in sol],'blocks':blocks,'cells':n,'rot':rot,'stages':st}
        else:
            print(f'  {fam:13s} nothing <=16 cells in budget',flush=True)
json.dump(out,open(sys.argv[1],'w'))
