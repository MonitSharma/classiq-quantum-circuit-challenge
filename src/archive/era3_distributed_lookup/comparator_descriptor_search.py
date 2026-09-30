"""Search for a class descriptor built only from interval (comparator) predicates.

The protected descriptor is a 3-bit loaded label plus one affine parity bit.
This asks whether the SAME 4-bit code can instead be produced by three interval
indicators [a <= t <= b] per axis, which a comparator/fold network can emit with
no QROM at all.  Interval predicates are the cheapest descriptor primitives the
repository already has measured native costs for.
"""
import itertools, sys
sys.path.insert(0, 'src')
import two_stage_oracle as ts


def label_tables(side, masks):
    cls = ts.ROWCLS if side == 'y' else ts.COLCLS
    return cls, [[sum(((v & m).bit_count() % 2) << i for i, m in enumerate(masks)) for v, _ in enumerate(cls)]]


def separates(cls, par, labs):
    """labs: list of 3 functions t -> bit.  Need class -> (par, l0,l1,l2) injective."""
    seen = {}
    for t in range(64):
        key = (par[t], labs[0][t], labs[1][t], labs[2][t])
        c = cls[t]
        if seen.setdefault(key, c) != c:
            return False
    return True


def search(side, max_intervals=600):
    cls = ts.ROWCLS if side == 'y' else ts.COLCLS
    intervals = []
    for a in range(64):
        for b in range(a, 64):
            ind = [1 if a <= t <= b else 0 for t in range(64)]
            if 0 < sum(ind) < 64:
                intervals.append(((a, b), ind))
    best = None
    parity_masks = [m for m in range(1, 64)]
    for pm in parity_masks:
        par = [(t & pm).bit_count() % 2 for t in range(64)]
        # greedy: pick the interval that splits classes best, then refine
        chosen = []
        cand = list(intervals)
        for _ in range(3):
            bestc, bestscore = None, None
            for (ab, ind) in cand:
                trial = chosen + [ind]
                # score: number of class-signature collisions under (par, trial...)
                sig = {}
                bad = 0
                for t in range(64):
                    key = (par[t],) + tuple(f[t] for f in trial)
                    c = cls[t]
                    if key in sig and sig[key] != c:
                        bad += 1
                    else:
                        sig[key] = c
                if bestscore is None or bad < bestscore:
                    bestscore, bestc = bad, (ab, ind)
            chosen.append(bestc[1])
            cand = [c for c in cand if c[0] != bestc[0]]
        if separates(cls, par, chosen):
            return pm, [c for c in chosen], None
    return None


if __name__ == '__main__':
    for side in ('x', 'y'):
        res = search(side)
        print(side, '->', 'FOUND' if res else 'none', res[0] if res else '')
        if res:
            par = [(t & res[0]).bit_count() % 2 for t in range(64)]
            print('   parity mask', res[0], 'label bits are interval indicators')
            # report the actual intervals by recomputing chosen ones
            cls = ts.ROWCLS if side == 'y' else ts.COLCLS
            labs = res[1]
            print('   label truth tables as intervals:')
            for f in labs:
                ones = [t for t in range(64) if f[t]]
                print('     [%d,%d]' % (min(ones), max(ones)), 'contiguous', ones == list(range(min(ones), max(ones) + 1)))
