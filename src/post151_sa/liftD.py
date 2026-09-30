"""Replace target 0 of a loader recipe with a mod-2pi-lifted (sparser) atom set."""
import pickle, sys, numpy as np
from codes import H, bits, xcode, ycode
from lift2 import lift_target, coeffs
from mkD3 import dump
src=sys.argv[1]; tag=sys.argv[2]; seeds=int(sys.argv[3]) if len(sys.argv)>3 else 40
D=pickle.load(open(src,'rb'))
side=D['side']; cols=D['cols']
code = xcode if side=='x' else ycode
B=bits(code)
combo=cols[0]
L=np.zeros(64,dtype=np.int64)
for j in range(3):
    if combo>>j&1: L^=B[j]
base=int(np.count_nonzero(H@L))
r=lift_target(L,seeds)
if r is None: print('no lift'); sys.exit(1)
g,w,k,e=r
a=coeffs(L,w)
rec=H@a
err=np.max(np.abs(np.remainder(rec-np.pi*L+np.pi,2*np.pi)-np.pi))
nz=[s for s in range(64) if abs(a[s])>1e-9]
print(f'{src} side {side} combo {combo}: {base} -> {len(nz)} atoms, err {err:.1e}')
if err>1e-9: sys.exit(1)
D2=dict(D); D2['targets']=dict(D['targets'])
D2['targets'][0]={(1<<6)|s: float(a[s]) for s in nz}
sz=dump(D2,tag)
print(tag,sz,'total',sum(sz.values()))
