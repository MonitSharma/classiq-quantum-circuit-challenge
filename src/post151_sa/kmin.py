"""Minimise the kernel's rotation count.

The kernel phase must satisfy  (H8 a)_v == M * L(v)  (mod 2M)  on the 182 specified
code pairs, with the other 74 entries free.  a_s/M * pi is the rotation angle, so a
finer granularity M gives a larger solution set and possibly a sparser support.
"""
import numpy as np, random, sys, time, json
sys.path.insert(0, '/work/cq/work')
from liftsa import consistent

H8 = np.array([[1]])
for _ in range(8): H8 = np.block([[H8, H8], [H8, -H8]])
H8 = H8.astype(np.int64)

idx = np.load('/work/cq/work/spec_idx.npy')
val = np.load('/work/cq/work/spec_val.npy')

def run(M, S0, seed, iters, tlimit):
    mod = 2 * M
    A = H8[idx]                    # 182 x 256
    b = (M * val) % mod
    rng = random.Random(seed)
    def feas(T): return consistent(A[:, T], b, mod)
    S = list(S0)
    ch = True
    while ch:
        ch = False
        order = S[:]; rng.shuffle(order)
        for s in order:
            T = [t for t in S if t != s]
            if T and feas(T): S = T; ch = True
    best = S[:]; cur = S[:]
    t0 = time.time()
    it = 0
    while time.time() - t0 < tlimit and it < iters:
        it += 1
        out = rng.choice(cur)
        pool = [t for t in range(256) if t not in cur]
        inn = rng.choice(pool)
        T = [t for t in cur if t != out] + [inn]
        if not feas(T): continue
        cur = T
        ch = True
        while ch:
            ch = False
            order = cur[:]; rng.shuffle(order)
            for s in order:
                U = [t for t in cur if t != s]
                if U and feas(U): cur = U; ch = True
        if len(cur) < len(best):
            best = cur[:]; print('   M=%d it %d support %d' % (M, it, len(best)), flush=True)
        if len(cur) > len(best) + 2: cur = best[:]
    return best

if __name__ == '__main__':
    co = np.array(json.load(open('/work/cq/artifacts/193/kernel_recipe.json'))['co'], float)
    a32 = np.round(co * 32).astype(np.int64)
    base = [s for s in range(256) if a32[s] != 0]
    print('base support', len(base), flush=True)
    for M in (32, 64, 128):
        S0 = [s * 1 for s in base] if M == 32 else list(range(256))
        if M != 32:
            # scale the known solution up to the finer grid as a starting point
            S0 = base
        t0 = time.time()
        best = run(M, S0, 11, 100000, float(sys.argv[1]) if len(sys.argv) > 1 else 600)
        print('M=%d (mod %d): minimum support found %d  [%.0fs]' % (M, 2 * M, len(best), time.time() - t0), flush=True)
        np.save('/work/cq/work/kmin_%d.npy' % M, np.array(sorted(best)))
