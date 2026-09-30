"""Does a feasible integer-lift support exist inside a union of few cosets of a
3-dimensional subspace V of F2^6?

If so the loader's main walk needs only three fixed source wires (a Gray code inside
each coset uses exactly the three generators of V), so the source-management CXs that
currently cost ~30% of the loader's gate count disappear.
"""
import numpy as np, itertools, sys, time, random
sys.path.insert(0, '/work/cq/work'); sys.path.insert(0, '/work/cq/src/post151_sa')
from liftsa import consistent

def subspaces3(n=6):
    """all 3-dimensional subspaces of F2^n, as sorted tuples of their 8 elements"""
    seen = set(); out = []
    for a in range(1, 1 << n):
        for b in range(a + 1, 1 << n):
            if b == a: continue
            for c in range(b + 1, 1 << n):
                el = {0, a, b, c, a ^ b, a ^ c, b ^ c, a ^ b ^ c}
                if len(el) != 8: continue
                key = tuple(sorted(el))
                if key in seen: continue
                seen.add(key); out.append(key)
    return out

def cosets(V, n=6):
    V = set(V); reps = []; seen = set()
    for v in range(1 << n):
        if v in seen: continue
        cs = tuple(sorted(v ^ w for w in V))
        reps.append(cs); seen |= set(cs)
    return reps

if __name__ == '__main__':
    from codes import xcode, ycode, bits, H
    side = sys.argv[1]; comb = int(sys.argv[2]); kmax = int(sys.argv[3])
    code = xcode if side == 'x' else ycode
    B = bits(code); L = np.zeros(64, dtype=np.int64)
    for j in range(3):
        if comb >> j & 1: L ^= B[j]
    b = (64 * L) % 128
    Hi = H.astype(np.int64)
    subs = subspaces3()
    print('3-dim subspaces:', len(subs), flush=True)
    t0 = time.time(); hits = []
    for V in subs:
        cs = cosets(V)
        for k in range(4, kmax + 1):
            found = False
            for pick in itertools.combinations(range(8), k):
                U = sorted(x for i in pick for x in cs[i])
                if consistent(Hi[:, U], b):
                    hits.append((k, V, tuple(pick), U)); found = True; break
            if found: break
        if time.time() - t0 > 900: print('time cap'); break
    if not hits:
        print('no coset-structured support found up to k =', kmax)
    else:
        hits.sort(key=lambda h: h[0])
        best = hits[0]
        print(f'BEST: {best[0]} cosets of V={best[1]}  support size <= {len(best[3])}', flush=True)
        ks = {}
        for k, V, pick, U in hits: ks[k] = ks.get(k, 0) + 1
        print('counts by number of cosets:', sorted(ks.items()))
        np.save(f'/work/cq/work/coset_{side}_{comb}.npy', np.array(best[3]))
        import pickle
        pickle.dump([(k, V, pick, U) for k, V, pick, U in hits[:40]],
                    open(f'/work/cq/work/coset_{side}_{comb}.pkl', 'wb'))
