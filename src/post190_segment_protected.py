import re
src=open('artifacts/190/two_stage_190.qasm').read()
stmts=[s.strip() for s in re.sub(r"//[^\n]*","",src).split(";") if s.strip()]
gates=stmts[3:]; W=18
coord=[frozenset(int(i) for i in re.findall(r"q\[(\d+)\]",st) if int(i)<12) for st in gates]
best=(0,0,0)
i=0
while i<len(gates):
    u=set(); j=i
    while j<len(gates):
        nu=u|coord[j]
        if len(nu)>2: break
        u=nu; j+=1
    if j-i>best[0]: best=(j-i,i,j)
    i+=1
ln,a,b=best
print(f'longest window with <=2 distinct coordinate wires: gates [{a},{b}) len {ln}')
print(f'  coordinate wires used there: {sorted(set().union(*coord[a:b])) if ln else []}')
def metrics(gs):
    dep=[0]*W; cx=0
    for st in gs:
        nm=st.split()[0].split('(')[0]
        qs=[int(i) for i in re.findall(r"q\[(\d+)\]",st)]
        if nm=='cx': cx+=1
        l=max(dep[q] for q in qs)+1
        for q in qs: dep[q]=l
    return max(dep),cx
for nm,gs in (('encoder',gates[:a]),('phase',gates[a:b]),('uncompute',gates[b:])):
    d,c=metrics(gs); print(f'  {nm:<11} gates {len(gs):5d}  depth {d:4d}  cx {c:4d}')
d,c=metrics(gates); print(f'  whole      gates {len(gates):5d}  depth {d:4d}  cx {c:4d}')
print()
print('audit budget: encoder <=50, phase <=35, uncompute <=50  => 135')
