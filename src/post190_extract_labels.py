"""Extract the six protected code-bit functions (3 per side) and characterise them."""
import sys, json; sys.path.insert(0,'src')
import two_stage_oracle as ts
def par(t,m): return bin(t&m).count('1')&1
d=json.load(open('artifacts/190/class_codes.json'))
ymask,xmask=d['ymask'],d['xmask']
ylab={tuple(map(int,k.split(','))):v for k,v in d['ylab'].items()}
xlab={tuple(map(int,k.split(','))):v for k,v in d['xlab'].items()}
def codes(lab,cls,mask):
    return [lab[(par(t,mask),cls[t])] for t in range(64)]
YC=codes(ylab,ts.ROWCLS,ymask); XC=codes(xlab,ts.COLCLS,xmask)
def anf(bits):
    a=list(bits)
    for i in range(6):
        for t in range(64):
            if t>>i & 1: a[t]^=a[t^(1<<i)]
    return [m for m in range(64) if a[m]]
FUNCS={}
for side,C in (('y',YC),('x',XC)):
    for b in range(3):
        tt=[(C[t]>>b)&1 for t in range(64)]
        mons=anf(tt)
        deg=max((bin(m).count('1') for m in mons), default=0)
        FUNCS[f'{side}{b}']=tt
        print(f'{side}{b}: weight {sum(tt):2d}/64  ANF terms {len(mons):2d}  degree {deg}')
# pairwise relations that a shared XAG could exploit
import itertools
print('\npairwise XOR weights (low weight => strong sharing):')
ks=list(FUNCS)
for a,b in itertools.combinations(ks,2):
    if a[0]!=b[0]: continue
    w=sum(FUNCS[a][t]^FUNCS[b][t] for t in range(64))
    print(f'  {a} ^ {b}: weight {w}')
print('\nAND-of-pairs check (is any f_i = f_j & f_k?):')
for a in ks:
    for b,c in itertools.combinations([k for k in ks if k!=a],2):
        if all(FUNCS[a][t]==(FUNCS[b][t]&FUNCS[c][t]) for t in range(64)):
            print(f'  {a} == {b} & {c}')
json.dump({k:v for k,v in FUNCS.items()},open(sys.argv[1],'w'))
print('\nsaved truth tables')
