"""Check the factored identities for v1 before building the circuit."""
def logo_level(x):
    ivs=[(32,48),(33,47),(34,46),(36,44),(38,42)]
    return sum(1 for lo,hi in ivs if lo<=x<=hi)
ok=True
for x in range(64):
    a=(x>>5)&1; b=(x>>4)&1; c=(x>>3)&1; d=(x>>2)&1; e=(x>>1)&1; g=x&1
    n=8*c+4*d+2*e+g
    G=a and not b; AB=a and b
    Zc=(n==0); X=(2<=n<=14); Y=(4<=n<=12); W=(6<=n<=10)
    V1 = G ^ (AB and Zc)
    V2 = G and not Zc
    V3 = G and X
    V4 = G and Y
    V5 = G and W
    lv=logo_level(x)
    exp=[lv>=1,lv>=2,lv>=3,lv>=4,lv>=5]
    got=[bool(V1),bool(V2),bool(V3),bool(V4),bool(V5)]
    if exp!=got:
        ok=False; print("mismatch at x=",x,exp,got)
print("factored thresholds exact:", ok)
# check the four-variable pieces as XOR/AND forms
bad=0
for n in range(16):
    c=(n>>3)&1; d=(n>>2)&1; e=(n>>1)&1; g=n&1
    P=c and d; Q=e and g
    Zc_f = (not (c or d)) and (not (e or g))
    X_f  = (c or d or e) and not (P and Q)
    Y_f  = (c or d) and not (P and (e or g))
    W_f  = ((not c) and d and e) ^ (c and (not d) and (not (e and g)))
    if Zc_f != (n==0): bad+=1; print("Zc",n)
    if X_f != (2<=n<=14): bad+=1; print("X",n)
    if Y_f != (4<=n<=12): bad+=1; print("Y",n)
    if W_f != (6<=n<=10): bad+=1; print("W",n)
print("four-variable forms exact:", bad==0)
