"""Joint anneal of class labels for encoder depth (relative-phase lookup) and
integer-lifted kernel cost. Masks follow artifacts/218: x parity 48, y parity 32."""
import sys, math, json, random, pickle, time
import numpy as np
import two_stage_oracle as ts
from post224_relative_lookup import relative
from post185_qcorr_oracle import kernel_terms

MASK = {'y': 32, 'x': 48}
CLS = {'y': ts.ROWCLS, 'x': ts.COLCLS}
DEGW = [0, 0.05, 0.5, 1, 4, 12, 30, 80, 200]

def keys(side):
    m = MASK[side]
    return sorted({((v & m).bit_count() % 2, c) for v, c in enumerate(CLS[side])})

def labels_to_code(side, lab):
    m = MASK[side]
    return [lab[((v & m).bit_count() % 2, c)] for v, c in enumerate(CLS[side])]

ENC_CACHE = {}
def enc_depth(side, lab, seeds):
    code = tuple(labels_to_code(side, lab))
    k = (side, code)
    if k not in ENC_CACHE:
        tab = np.array([[math.pi * (c >> b & 1) for c in code] for b in range(3)])
        ENC_CACHE[k] = min(relative(tab, s)[0].depth() for s in seeds)
    return ENC_CACHE[k]

def full_code(side, lab):
    m = MASK[side]
    return [((v & m).bit_count() % 2) | (lab[((v & m).bit_count() % 2, c)] << 1)
            for v, c in enumerate(CLS[side])]

def kcost(yl, xl):
    terms = kernel_terms(full_code('x', xl), full_code('y', yl))
    return sum(DEGW[t.bit_count()] for t in terms), terms

def score(yl, xl, seeds, w):
    ey = enc_depth('y', yl, seeds); ex = enc_depth('x', xl, seeds)
    kc, terms = kcost(yl, xl)
    return 2 * max(ey, ex) + w * kc, ey, ex, kc, terms

def main(seed, steps, w):
    rng = random.Random(seed)
    seeds = range(8)
    lab = {}
    base = json.load(open('/Users/monitsharma/Downloads/classiq/artifacts/218/class_codes.json'))
    from post258_two_stage_anf import decode
    yl = decode(base['ylab']); xl = decode(base['xlab'])
    if seed % 2:  # random start on odd seeds
        for L, side in ((yl, 'y'), (xl, 'x')):
            for b in (0, 1):
                ks = [k for k in keys(side) if k[0] == b]
                for k, v in zip(ks, rng.sample(range(8), len(ks))):
                    L[k] = v
    cur = score(yl, xl, seeds, w); best = (cur, dict(yl), dict(xl))
    print('start', cur[:4], flush=True)
    for st in range(steps):
        side = rng.choice('yx'); L = yl if side == 'y' else xl
        k = rng.choice(keys(side)); val = rng.randrange(8)
        other = next((o for o in keys(side) if o[0] == k[0] and L[o] == val and o != k), None)
        prev = L[k]; L[k] = val
        if other: L[other] = prev
        new = score(yl, xl, seeds, w)
        T = 3 * (1 - st / steps) + 0.3
        if new[0] <= cur[0] or rng.random() < math.exp((cur[0] - new[0]) / T):
            cur = new
            if new[0] < best[0][0]:
                best = (new, dict(yl), dict(xl))
                print(st, 'score', round(new[0], 1), 'ey', new[1], 'ex', new[2], 'kcost', new[3], flush=True)
        else:
            L[k] = prev
            if other: L[other] = val
    enc = lambda d: {','.join(map(str, k)): v for k, v in d.items()}
    out = dict(score=best[0][0], ey=best[0][1], ex=best[0][2], cost=best[0][3], terms=best[0][4],
               ylab=enc(best[1]), xlab=enc(best[2]), xmask=48, ymask=32, w=w, seed=seed)
    json.dump(out, open(f'/private/tmp/claude-501/-Users-monitsharma-Downloads-classiq/2c32fabd-bc16-4814-a999-708a83f95240/scratchpad/joint_{seed}_{w}.json', 'w'))
    print('FINAL', out['score'], out['ey'], out['ex'], out['cost'], len(out['terms']), flush=True)

if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3]))
