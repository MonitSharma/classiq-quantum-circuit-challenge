"""Can the mod-2pi lift remove the address-bit-5 atoms from the y unconditional target?
If yes, wire 5 (which holds y5 = the py code vector from time 0) could freeze immediately."""
import numpy as np, sys, time
sys.path.insert(0, '.')
from codes import xcode, ycode, bits, H
code = ycode
B = bits(code); cols = (1, 2, 4)
Bn = np.array([sum(B[i] for i in range(3) if cols[j] >> i & 1) % 2 for j in range(3)])
L = Bn[0].astype(np.int64)
Hl = H.astype(np.int64)
Y = Hl @ L
b5 = np.array([(s >> 5) & 1 for s in range(64)], dtype=bool)
print('raw support size', int(np.count_nonzero(Y)), ' of which bit-5:', int(np.count_nonzero(Y[b5])))
print('raw support bit-5 classes:',
      {int(v): int(np.sum((Y[b5] % 4) == v)) for v in (0, 1, 2, 3)})
rng = np.random.default_rng(5)
Hc = Hl.copy()
z = np.zeros(64, np.int64); T = Y + 2 * (Hc @ z)
best = int(np.count_nonzero(T[b5])); bestz = z.copy()
t0 = time.time(); it = 0; cur = best
while time.time() - t0 < 60:
    it += 1
    f = int(rng.integers(64)); d = 1 if rng.random() < 0.5 else -1
    newT = T + 2 * d * Hc[:, f]
    c = int(np.count_nonzero(newT[b5]))
    if c <= cur or rng.random() < 0.02:
        T = newT; z[f] += d; cur = c
    if c < best:
        best = c; bestz = z.copy(); print('  bit-5 atoms now', best, flush=True)
    if it % 5000 == 0 and cur > best + 2:
        z = bestz.copy(); T = Y + 2 * (Hc @ z); cur = int(np.count_nonzero(T[b5]))
print(f'y label0: bit-5 atoms raw {int(np.count_nonzero(Y[b5]))} -> best {best} in {it} iters')
