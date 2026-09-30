"""Direct integer local search on the mod-2pi shift z for the UNCONDITIONAL loader target.

target[f] = pi*(L[f] + 2 z[f]);  coefficients a_s = (pi/64)*(Y[s] + 2*(H z)[s]).
Support = #{s : Y[s] + 2*(Hz)[s] != 0}.  H z is O(64) per move, so this is a pure cheap search.
"""
import numpy as np, sys, time, pickle
sys.path.insert(0, '.')
from codes import xcode, ycode, bits, H

def setup(side):
    code = xcode if side == 'x' else ycode
    B = bits(code)
    cols = (1, 2, 6) if side == 'x' else (1, 2, 4)
    Bn = np.array([sum(B[i] for i in range(3) if cols[j] >> i & 1) % 2 for j in range(3)])
    L = Bn[0].astype(np.int64)
    Y = H.astype(np.int64) @ L
    return L, Y

def cost(T): return int(np.count_nonzero(T))

def search(side, seconds=60, seed=0):
    L, Y = setup(side)
    Hl = H.astype(np.int64)
    Hc = Hl.copy()                       # H[s][f]
    rng = np.random.default_rng(seed)
    z = np.zeros(64, np.int64)
    Hz = Hc @ z
    T = Y + 2 * Hz
    best = cost(T); bestz = z.copy()
    t0 = time.time(); it = 0
    cur = best
    while time.time() - t0 < seconds:
        it += 1
        f = int(rng.integers(64)); d = 1 if rng.random() < 0.5 else -1
        newT = T + 2 * d * Hc[:, f]
        c = cost(newT)
        if c <= cur or rng.random() < 0.02:
            T = newT; z[f] += d; Hz = Hz + d * Hc[:, f]; cur = c
        if c < best:
            best = c; bestz = z.copy()
            print(f'  it {it} support {best}', flush=True)
        if it % 4000 == 0 and cur > best + 3:
            # restart from best with a kick
            z = bestz.copy(); Hz = Hc @ z; T = Y + 2 * Hz; cur = cost(T)
            for _ in range(3):
                ff = int(rng.integers(64)); dd = 1 if rng.random() < 0.5 else -1
                z[ff] += dd; Hz = Hz + dd * Hc[:, ff]
            T = Y + 2 * Hz; cur = cost(T)
    print(f'{side} label0: raw {cost(Y + 2*(Hc@np.zeros(64,np.int64)))} -> best {best} in {it} iters', flush=True)
    np.save(f'runs/zsa_{side}_0.npy', bestz)
    return bestz, best

if __name__ == '__main__':
    for side in sys.argv[1:]:
        search(side, seconds=float(os.environ.get('SECS', '90')) if (os := __import__('os')) else 90, seed=int(os.environ.get('SEED', '1')))
