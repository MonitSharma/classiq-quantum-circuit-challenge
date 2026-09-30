"""Ring-predicate label search.

The y classes are exactly the cells cut out by the two families of nested
intervals around 19 and 41 plus the square interval.  If three label bits can be
built from unions/intersections of those ring predicates, the encoder becomes a
handful of comparators instead of a 77-layer QROM, and the kernel is untouched
because the 4-bit code is the same object.
"""
import itertools, sys
sys.path.insert(0, 'src')
import two_stage_oracle as ts

BASE = {
    'R19_2': (17, 21), 'R19_4': (15, 23), 'R19_6': (13, 25), 'R19_7': (12, 26), 'R19_8': (11, 27),
    'R41_2': (39, 43), 'R41_4': (37, 45), 'R41_5': (36, 46), 'R41_6': (35, 47),
    'SQ': (29, 53), 'BAND1': (32, 63), 'BAND0': (0, 31), 'TOP': (54, 63), 'BOT': (0, 10),
}


def tt(a, b):
    return [1 if a <= t <= b else 0 for t in range(64)]


def build_library():
    base = {k: tt(*v) for k, v in BASE.items()}
    lib = dict(base)
    names = list(base)
    for a, b in itertools.combinations(names, 2):
        lib[f'{a}|{b}'] = [x | y for x, y in zip(base[a], base[b])]
        lib[f'{a}&{b}'] = [x & y for x, y in zip(base[a], base[b])]
    # drop constant / full functions
    out = {}
    for k, v in lib.items():
        s = sum(v)
        if 0 < s < 64:
            out[k] = v
    return out


def separates(cls, par, labs):
    seen = {}
    for t in range(64):
        key = (par[t], labs[0][t], labs[1][t], labs[2][t])
        c = cls[t]
        if seen.setdefault(key, c) != c:
            return False
    return True


def search(side):
    cls = ts.ROWCLS if side == 'y' else ts.COLCLS
    lib = build_library()
    names = list(lib)
    results = []
    for pm in range(1, 64):
        par = [(t & pm).bit_count() % 2 for t in range(64)]
        # greedy forward selection
        chosen, pool = [], names[:]
        for _ in range(3):
            best, bestbad = None, None
            for nm in pool:
                trial = chosen + [nm]
                sig, bad = {}, 0
                for t in range(64):
                    key = (par[t],) + tuple(lib[f][t] for f in trial)
                    c = cls[t]
                    if key in sig and sig[key] != c:
                        bad += 1
                    else:
                        sig[key] = c
                if bestbad is None or bad < bestbad:
                    bestbad, best = bad, nm
            chosen.append(best)
            pool = [p for p in pool if p != best]
        if separates(cls, par, [lib[c] for c in chosen]):
            results.append((pm, chosen))
    return results


if __name__ == '__main__':
    for side in ('y', 'x'):
        res = search(side)
        print(f'==== {side}: {len(res)} separating parity+triple(s)')
        for pm, names in res[:6]:
            print('   parity mask', pm, 'bits:', names)
