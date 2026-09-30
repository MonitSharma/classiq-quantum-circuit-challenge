"""Search for a separating class label drawn from cheap comparator predicates.

The QROM encoder costs 77 native layers because it walks a six-variable address.
A comparator costs ~25 layers for a full six-bit comparison, so if the three
loaded label bits can be produced by a handful of interval predicates the same
4-bit code becomes far cheaper WITHOUT changing the kernel, because the code
itself is unchanged.

Criterion (exact): the code (parity, l0, l1, l2) must separate classes, i.e.
    cls[t] != cls[u]  =>  code[t] != code[u].
"""
import itertools, sys, random
sys.path.insert(0, 'src')
import two_stage_oracle as ts


def separates(cls, code, par):
    seen = {}
    for t in range(64):
        key = (par[t], code[0][t], code[1][t], code[2][t])
        c = cls[t]
        if seen.setdefault(key, c) != c:
            return False
    return True


def library():
    """Interval predicates and their intersections with the top coordinate bit."""
    cands = []
    for a in range(64):
        for b in range(a, 64):
            ind = [1 if a <= t <= b else 0 for t in range(64)]
            n = sum(ind)
            if 0 < n < 64:
                cands.append((f'[{a},{b}]', ind))
    return cands


def greedy(side, parmask, tries=6):
    cls = ts.ROWCLS if side == 'y' else ts.COLCLS
    par = [(t & parmask).bit_count() % 2 for t in range(64)]
    lib = library()
    best = None
    for trial in range(tries):
        rng = random.Random(trial)
        pool = lib[:]
        rng.shuffle(pool)
        chosen = []
        for step in range(3):
            bestc, bestbad = None, None
            for name, ind in pool:
                trial_set = chosen + [ind]
                sig = {}
                bad = 0
                for t in range(64):
                    key = (par[t],) + tuple(f[t] for f in trial_set)
                    c = cls[t]
                    if key in sig and sig[key] != c:
                        bad += 1
                    else:
                        sig[key] = c
                if bestbad is None or bad < bestbad:
                    bestbad, bestc = bad, (name, ind)
            chosen.append(bestc[1])
            pool = [p for p in pool if p[0] != bestc[0]]
        if separates(cls, chosen, par):
            return parmask, [c for c in chosen], None
        if best is None or bestbad < best[2]:
            best = (parmask, chosen, bestbad)
    return None


if __name__ == '__main__':
    for side in ('y', 'x'):
        found = None
        for pm in range(1, 64):
            r = greedy(side, pm, tries=2)
            if r:
                found = r
                break
        if found:
            pm, labs, _ = found
            print(side, 'FOUND parity mask', pm, 'with 3 interval indicators')
            for f in labs:
                ones = [t for t in range(64) if f[t]]
                contig = ones == list(range(min(ones), max(ones) + 1))
                print('   interval [%d,%d] contiguous=%s' % (min(ones), max(ones), contig))
        else:
            print(side, 'no 3-interval label found over all parity masks')
