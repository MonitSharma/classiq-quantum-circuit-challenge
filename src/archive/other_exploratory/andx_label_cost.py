"""AND-XOR complexity of the loaded class label.

The QROM encoder costs 77 layers for three arbitrary 6-input functions.  A
hand-built encoder only wins if the label functions are far simpler than
arbitrary.  This anneals the free class-to-label assignment to minimise the
total algebraic-normal-form weight of the three label bits (the standard proxy
for XOR-AND network size), and reports the degree profile.

If the minimum stays in the tens of terms with high degree, no shallow AND-XOR
encoder exists and the QROM is already the efficient choice.
"""
import itertools, json, math, random, sys
from collections import Counter
sys.path.insert(0, 'src')
import two_stage_oracle as ts

MASKS = {'x': (6, 16, 48, 60), 'y': (32,)}


def cells(side, mask):
    cls = ts.ROWCLS if side == 'y' else ts.COLCLS
    return cls, sorted({((v & mask).bit_count() % 2, c) for v, c in enumerate(cls)})


def anf_terms(f, n=6):
    a = f[:]
    for i in range(n):
        for m in range(1 << n):
            if m >> i & 1:
                a[m] ^= a[m ^ (1 << i)]
    return [m for m in range(1, 1 << n) if a[m]]


def cost(side, mask, lab):
    cls, _ = cells(side, mask)
    code = [lab[((v & mask).bit_count() % 2, c)] for v, c in enumerate(cls)]
    total, deg = 0, Counter()
    for b in range(3):
        f = [0] * 64
        for v in range(64):
            if (code[v] >> b) & 1:
                f[v] = 1
        terms = anf_terms(f)
        total += len(terms)
        for m in terms:
            deg[bin(m).count('1')] += 1
    return total, deg


def random_lab(side, mask, rng):
    cls, cl = cells(side, mask)
    lab = {}
    for b in (0, 1):
        group = [c for (p, c) in cl if p == b]
        vals = list(range(8)); rng.shuffle(vals)
        for c in group:
            lab[(b, c)] = vals.pop()
    return lab


def anneal(side, mask, seconds, seed):
    rng = random.Random(seed)
    lab = random_lab(side, mask, rng)
    cur, _ = cost(side, mask, lab)
    best, bestlab = cur, dict(lab)
    import time
    t0 = time.time()
    while time.time() - t0 < seconds:
        cls, cl = cells(side, mask)
        b = rng.randrange(2)
        group = [c for (p, c) in cl if p == b]
        if len(group) < 2:
            continue
        a, c = rng.sample(group, 2)
        lab[(b, a)], lab[(b, c)] = lab[(b, c)], lab[(b, a)]
        new, _ = cost(side, mask, lab)
        if new <= cur or rng.random() < math.exp((cur - new) / max(1.0, 0.1 * cur)):
            cur = new
            if new < best:
                best, bestlab = new, dict(lab)
        else:
            lab[(b, a)], lab[(b, c)] = lab[(b, c)], lab[(b, a)]
    return best, bestlab


if __name__ == '__main__':
    out = {}
    for side in ('y', 'x'):
        for mask in MASKS[side]:
            best = None
            for seed in range(3):
                b, lab = anneal(side, mask, 20, seed)
                if best is None or b < best[0]:
                    best = (b, lab)
            total, deg = cost(side, mask, best[1])
            # baseline: the protected assignment
            base = json.loads(open('artifacts/185/class_codes.json').read())
            from post258_two_stage_anf import decode
            bl = decode(base[side + 'lab'])
            btotal, bdeg = cost(side, mask, bl)
            print(f'{side} mask {mask}: protected ANF {btotal} terms {dict(bdeg)} | '
                  f'annealed {total} terms {dict(deg)}', flush=True)
            out[f'{side}_{mask}'] = dict(protected=btotal, annealed=total,
                                         degree=dict(deg), best_degree=dict(bdeg))
    open('artifacts/andx_cost.json', 'w').write(json.dumps(out, indent=2))
