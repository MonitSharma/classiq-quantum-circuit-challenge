import pickle, sys, math, json
sys.path.insert(0, '.')
import numpy as np
from kdrv import KTERMS, CO
R = '../../artifacts/118/recipes/'

# ---- 1. blocked-term counts per code direction (the BLKW weights) ----
print('=== blocked-term counts over the 63 kernel terms ===')
names = ['py', 'Ly0', 'Ly1', 'Ly2', 'px', 'Lx0', 'Lx1', 'Lx2']
for i, nm in enumerate(names):
    cnt = sum(1 for m in KTERMS if (m >> i) & 1)
    print(f'  bit {i} {nm}: {cnt}')

# ---- 2. the hyperplane claim for the unconditional target ----
print()
print('=== mod-2pi lift: which Walsh coefficients are killable ===')
for side, f in (('x', 'x_support_89'), ('y', 'y_support_89')):
    D = pickle.load(open(R + f + '.pkl', 'rb'))
    tg = D['targets'][0]
    # rebuild L(x) on 64 inputs from the atom list: L(x) = sum of atom incidence / pi
    L = [0] * 64
    for mask, ang in tg.items():
        # atom mask is over the 9 wires (z0..z5, t0..t2); the target bit is t_0
        par = mask & 0x3F
        bit = (mask >> 6) & 1          # target t0 must be 1 for an unconditional atom
        sign = -1 if bit else 1
        for z in range(64):
            L[z] += sign * ((-1) ** bin(z & par).count('1'))
    # each L(z) should be +-pi
    ok = all(abs(abs(v) - math.pi) < 1e-6 for v in L)
    bits = [1 if v > 0 else 0 for v in L]
    v = 0
    for z, b in enumerate(bits):
        if b: v ^= z
    killable = [S for S in range(64) if (bin(S & v).count('1') % 2) == 0]
    print(f'  {side}: target-0 atoms {len(tg)}, L +-pi on all 64: {ok}, '
          f'|support(L)| = {sum(bits)}, v = {v}, |v^perp| = {len(killable)}')
