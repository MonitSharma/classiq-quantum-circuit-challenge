"""2 in-place code wires realised as a pure shift: block(t,f) = t XOR s(f).
s depends on all four free wires -> two 4-control UCRys = 16 rotations each.
Need <=4 classes per block (two ancilla bits finish the separation)."""
import sys, itertools, json, time; sys.path.insert(0,'src')
from collections import Counter
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
    return C, full

def solve(cls, gen, cap=4):
    C,full=basis(list(gen))
    grid=[[None]*4 for _ in range(16)]
    for y in range(64):
        c=C(y); grid[(c>>2)&15][c&3]=cls[y]
    blocks=[set() for _ in range(4)]; sol=[None]*16
    def rec(f):
        if f==16: return True
        for s in range(4):
            added=[];ok=True
            for t in range(4):
                b=t^s; c=grid[f][t]
                if c not in blocks[b]:
                    if len(blocks[b])>=cap: ok=False;break
                    blocks[b].add(c); added.append((b,c))
            if ok:
                sol[f]=s
                if rec(f+1): return True
            for b,c in added: blocks[b].discard(c)
        return False
    return (list(sol),[sorted(b) for b in blocks],full) if rec(0) else None

W2=subspaces2()
out={}
for name,cls in (('y',ts.ROWCLS),('x',ts.COLCLS)):
    tot=Counter(cls); cands=[]
    for W,gen in W2:
        seen=set(); rows=[]
        for y in range(64):
            if y in seen: continue
            co=[y^w for w in W]; seen.update(co); rows.append(co)
        need=sum(max(max(sum(1 for t in r if cls[t]==c) for r in rows), -(-n//16)) for c,n in tot.items())
        if need<=16: cands.append((need,gen))
    cands.sort()
    got=None; t0=time.time()
    for need,gen in cands:
        r=solve(cls,gen)
        if r: got=(gen,r); break
    print(f'{name}: {len(cands)} candidates -> '
          f'{"SHIFT SAT gen="+str(got[0]) if got else "shift infeasible"} ({time.time()-t0:.0f}s)',flush=True)
    if got:
        print(f'   shifts={got[1][0]}')
        print(f'   blocks={got[1][1]}',flush=True)
        out[name]={'gen':list(got[0]),'shifts':got[1][0],'blocks':got[1][1],'basis':got[1][2]}
json.dump(out,open(sys.argv[1],'w'))
