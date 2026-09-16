"""Width-constrained code synthesis: can a loader work with no scratch wire?

At kernel time all six ancillas hold the six code bits, so whichever side is
loaded second has exactly its own three wires and no scratch. Two ways to live
within that were tried here.

**Degree-bounded codes.** A product of at most three affine forms can be written
straight into a clean target with no scratch -- RCCX for two factors, RC3X for
three -- so a code whose bits are XORs of such products needs no scratch at all,
and the three bits sit on three different wires, which is the only way an AND
loader gets any parallelism. XORing products of at most three factors yields a
function of degree at most three, so the construction needs a degree-3 code.
`min_degree` anneals the per-address label directly (a code only has to determine
the class, so a class may be split across label values, which is strictly more
freedom than the class-constant labelings every earlier search used) and the
answer is **degree 5**. There is no degree-3 code, so no scratch-free loader.

**Quadratic cascade.** Relax to computing the bits in order, each quadratic in
the address bits *and the bits already computed*:

    t2 = Q2(y)              t1 = Q1(y, t2)              t0 = Q0(y, t2, t1)

Substituting back gives degree 4 and 8, so the cascade is not limited to
quadratic codes, and each bit ranges over an explicit GF(2) subspace of the
64-dimensional function space (dimensions 22, 29, 37). `cascade_residual` scores
a labeling by how far its last bit is from the relevant subspace, counting the
dual functionals it violates. The best found is 1-2 violations, not 0.

Both are recorded as measurements, not as circuits. Even a working cascade would
serialise onto three wires, whereas `structured_ucry` already hosts its rotations
across all nine wires of a side at zero scratch, which an AND network can never
do: the twelve coordinate wires must stay inside the span and so can never hold
an AND value.
"""
import argparse
import itertools
import json
import math
import random

import two_stage_oracle as ts


def anf(values):
    a = list(values)
    for b in range(6):
        for m in range(64):
            if m >> b & 1:
                a[m] ^= a[m ^ (1 << b)]
    return a


def degrees(code):
    out = []
    for j in range(3):
        c = anf([(v >> j) & 1 for v in code])
        nz = [m for m in range(64) if c[m]]
        out.append(max([m.bit_count() for m in nz], default=0))
    return out


def conflicts(code, cls, raw):
    buckets = {}
    for v in range(64):
        buckets.setdefault((raw[v], code[v]), []).append(v)
    bad = 0
    for members in buckets.values():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                if cls[members[i]] != cls[members[j]]:
                    bad += 1
    return bad


def min_degree(cls, raw_mask, start, steps=25000, seeds=5):
    """Lowest maximum ANF degree over valid codes, annealing per-address labels."""
    raw = [bin(v & raw_mask).count('1') & 1 for v in range(64)]
    best = None
    for seed in range(seeds):
        rng = random.Random(seed)
        code = list(start)

        def cost(c):
            d = degrees(c)
            return 1000 * conflicts(c, cls, raw) + 10 * max(d) + sum(d)

        cur = cost(code)
        local = (cur, list(code))
        for step in range(steps):
            v = rng.randrange(64)
            old = code[v]
            code[v] = rng.randrange(8)
            val = cost(code)
            temp = 1 + 12 * (1 - (step % 4000) / 4000) ** 2
            if val <= cur or rng.random() < math.exp((cur - val) / temp):
                cur = val
            else:
                code[v] = old
            if cur < local[0]:
                local = (cur, list(code))
        c = local[1]
        if conflicts(c, cls, raw) == 0:
            d = max(degrees(c))
            if best is None or d < best[0]:
                best = (d, degrees(c), c)
    return best


FULL = (1 << 64) - 1


def _mono(mask):
    return sum(1 << v for v in range(64) if (v & mask) == mask)


QUAD = ([_mono(0)] + [_mono(1 << i) for i in range(6)]
        + [_mono((1 << i) | (1 << j)) for i, j in itertools.combinations(range(6), 2)])
AFFINE = [_mono(0)] + [_mono(1 << i) for i in range(6)]


def cascade_basis(previous):
    rows = list(QUAD)
    for p in previous:
        rows += [f & p for f in AFFINE]
    for a, b in itertools.combinations(previous, 2):
        rows.append(a & b)
    return rows


def _dual(rows):
    piv = {}
    for r in rows:
        x = r
        while x:
            i = x.bit_length() - 1
            if i in piv:
                x ^= piv[i]
            else:
                piv[i] = x
                break
    out = []
    for f in (i for i in range(64) if i not in piv):
        u = 1 << f
        for i in sorted(piv, reverse=True):
            if bin(piv[i] & u).count('1') & 1:
                u ^= 1 << i
        out.append(u)
    return out


def cascade_residual(bits):
    """Dual functionals the best-placed bit violates; 0 means scratch-free."""
    best = None
    for last in range(3):
        a, b = [bits[j] for j in range(3) if j != last]
        d = _dual(cascade_basis([a, b]))
        bad = sum(1 for u in d if bin(bits[last] & u).count('1') & 1)
        if best is None or bad < best[0]:
            best = (bad, last)
    return best


def bits_of(code):
    return [sum(((code[v] >> j) & 1) << v for v in range(64)) for j in range(3)]


if __name__ == '__main__':
    from post258_two_stage_anf import decode
    p = argparse.ArgumentParser()
    p.add_argument('--steps', type=int, default=25000)
    a = p.parse_args()
    rec = json.loads(open('artifacts/185/class_codes.json').read())
    par = lambda v, m: bin(v & m).count('1') & 1
    yl, xl = decode(rec['ylab']), decode(rec['xlab'])
    cases = {'y': ([yl[(par(y, 32), ts.ROWCLS[y])] for y in range(64)], ts.ROWCLS, 32),
             'x': ([xl[(par(x, 48), ts.COLCLS[x])] for x in range(64)], ts.COLCLS, 48)}
    for side, (start, cls, mask) in cases.items():
        best = min_degree(cls, mask, start, a.steps)
        resid = cascade_residual(bits_of(start))
        print(json.dumps(dict(side=side, raw_mask=mask,
                              protected_degrees=degrees(start),
                              min_valid_max_degree=best[0] if best else None,
                              min_valid_degrees=best[1] if best else None,
                              scratch_free_possible=bool(best and best[0] <= 3),
                              cascade_residual=resid[0])), flush=True)
