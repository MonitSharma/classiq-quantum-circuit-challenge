"""Layer-by-layer occupancy of the protected encoder (gates 0..753)."""
import re
from collections import Counter
src=open('artifacts/190/two_stage_190.qasm').read()
st=[s.strip() for s in re.sub(r"//[^\n]*","",src).split(";") if s.strip()][3:]
enc=st[:754]
W=18
dep=[0]*W; layers={}
for g in enc:
    nm=g.split()[0].split('(')[0]
    qs=[int(i) for i in re.findall(r"q\[(\d+)\]",g)]
    l=max(dep[q] for q in qs)+1
    for q in qs: dep[q]=l
    layers.setdefault(l,[]).append((nm,tuple(qs)))
D=max(layers)
cx_per=[0]*(D+1); u3_per=[0]*(D+1)
for l,gs in layers.items():
    for nm,qs in gs:
        if nm=='cx': cx_per[l]+=1
        else: u3_per[l]+=1
print(f'encoder depth {D}, gates {len(enc)}')
tot_cx=sum(cx_per); tot_u3=sum(u3_per)
print(f'  cx {tot_cx}  u3 {tot_u3}')
occ=Counter()
for l in range(1,D+1):
    used=2*cx_per[l]+u3_per[l]
    occ[(cx_per[l],u3_per[l])]+=1
print('\nlayers with zero rotations (pure CX):',sum(1 for l in range(1,D+1) if u3_per[l]==0))
print('layers with zero CX (pure rotation):',sum(1 for l in range(1,D+1) if cx_per[l]==0))
print(f'mean wire occupancy: {sum(2*cx_per[l]+u3_per[l] for l in range(1,D+1))/(D*W)*100:.0f}% of 18 wires')
print(f'rotations per layer: {tot_u3/D:.2f}   (ceiling 6 for CX-paired rotations)')
print('\nmost common (cx,u3) layer profiles:')
for k,v in occ.most_common(10): print(f'   cx={k[0]} u3={k[1]}: {v} layers')
