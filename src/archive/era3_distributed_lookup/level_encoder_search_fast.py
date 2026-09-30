"""Depth-aware AND-network search for a level encoder with fixed target code bits.

The earlier searches ranked states by the best separating triple, which made
scoring expensive enough that operands had to be sampled.  Fixing the three
target functions up front (the code is chosen by the kernel search instead)
makes a state worth only three residual reductions, so the whole operand family
can be enumerated at every step.

Scoring is incremental.  For each register k we precompute a basis of the other
eight registers plus the constant, and the residuals of the three targets
against it.  A candidate that writes ``p`` into register k then costs a handful
of operations: reduce ``regs[k] ^ p`` against that basis and fold the result
into the three precomputed residuals.

States are ranked by residual first and by the resulting AND depth second,
because circuit depth, not AND count, is what the oracle is scored on.

Usage:  python src/level_encoder_search_fast.py <name> <code-index> <seconds> <outdir>
"""
import json
import sys
import time
from itertools import combinations
from pathlib import Path

FULL = (1 << 64) - 1
VARS = [sum(((t >> i) & 1) << t for t in range(64)) for i in range(6)]


def _rng(a, b):
    return set(range(a, b + 1))


NESTED = {
    'u1': [_rng(11, 27), _rng(12, 26), _rng(13, 25), _rng(15, 23), _rng(17, 21)],
    'v1': [_rng(32, 48), _rng(33, 47), _rng(34, 46), _rng(36, 44), _rng(38, 42)],
    'u2': [_rng(29, 53), _rng(35, 47), _rng(36, 46), _rng(37, 45), _rng(39, 43)],
    'v2': [_rng(2, 61), _rng(2, 26) | _rng(50, 60), _rng(2, 26) | _rng(51, 59),
           _rng(2, 26) | _rng(53, 57), _rng(2, 26)],
}

# Code pairs whose six-variable kernel transpiles shallowest, from the kernel
# sweep in level_oracle.kernel_terms.  Each entry is (y-triple, x-triple) as
# subsets of the six level values.
CODES = [
    ((0b111000, 0b110100, 0b100110), (0b010100, 0b100010, 0b111000)),
    ((0b111100, 0b110010, 0b101010), (0b111000, 0b110100, 0b100110)),
    ((0b110000, 0b111100, 0b101010), (0b100100, 0b111000, 0b001010)),
]


def targets_for(name, triple):
    levels = [sum(1 for s in NESTED[name] if t in s) for t in range(64)]
    return [sum(1 << t for t in range(64) if (sub >> levels[t]) & 1) for sub in triple]


def basis_of(vectors):
    piv = {}
    for v in vectors:
        for b in range(63, -1, -1):
            if v >> b & 1:
                if b in piv:
                    v ^= piv[b]
                else:
                    piv[b] = v
                    break
    return piv


def reduce_by(v, piv):
    for b in range(63, -1, -1):
        if v >> b & 1 and b in piv:
            v ^= piv[b]
    return v


def operand_family(regs, depths, max_terms=3):
    """Every XOR of at most `max_terms` registers, with and without complement."""
    out = {}
    for n in range(1, max_terms + 1):
        for idxs in combinations(range(9), n):
            v = 0
            d = 0
            for i in idxs:
                v ^= regs[i]
                d = max(d, depths[i])
            for w in (v, v ^ FULL):
                if w in (0, FULL):
                    continue
                if w not in out or out[w] > d:
                    out[w] = d
    return out


def expand(regs, depths, targets):
    """Yield (score, and_depth, p, k, a, b) for every candidate single AND."""
    pre = []
    for k in range(9):
        piv = basis_of([regs[i] for i in range(9) if i != k] + [FULL])
        pre.append((piv, [reduce_by(t, piv) for t in targets]))
    fam = operand_family(regs, depths)
    items = sorted(fam.items())
    out = []
    seen = set()
    for ai in range(len(items)):
        a, da = items[ai]
        for bi in range(ai + 1, len(items)):
            b, db = items[bi]
            p = a & b
            if p in (0, FULL):
                continue
            pdep = max(da, db) + 1
            for k in range(9):
                key = (p, k)
                if key in seen:
                    continue
                seen.add(key)
                piv, base = pre[k]
                v = reduce_by(regs[k] ^ p, piv)
                lead = v.bit_length() - 1 if v else -1
                score = 0
                for r in base:
                    if lead >= 0 and (r >> lead) & 1:
                        r ^= v
                    score += r.bit_count()
                out.append((score, max(pdep, depths[k]), p, k, a, b))
    return out


def span_elements(regs):
    """Every element of the affine span of the registers (dimension is at most 9)."""
    basis = []
    piv = {}
    for v in list(regs) + [FULL]:
        w = v
        for b in range(63, -1, -1):
            if w >> b & 1:
                if b in piv:
                    w ^= piv[b]
                else:
                    piv[b] = w
                    basis.append(w)
                    break
    out = [0]
    for e in basis:
        out += [x ^ e for x in out]
    return out


def span_dim(regs):
    piv = {}
    d = 0
    for v in regs:
        w = v
        for b in range(63, -1, -1):
            if w >> b & 1:
                if b in piv:
                    w ^= piv[b]
                else:
                    piv[b] = w
                    d += 1
                    break
    return d


def coset_weight(targets, regs):
    """Sum over targets of the minimum Hamming weight in the target's coset.

    The Gaussian residual is only one representative of the coset; the smallest
    one is a far better measure of how close a target is to being reachable, and
    the span is small enough to enumerate.
    """
    elems = span_elements(regs)
    total = 0
    for t in targets:
        total += min((t ^ e).bit_count() for e in elems)
    return total


def exact_completions(targets, regs):
    """Find single ANDs that put a still-missing target exactly into the span.

    A residual of low Hamming weight is never closed by chance: the product has
    to land in one specific coset out of 2**(64-dim).  It only happens when the
    target genuinely factors, as ``[34,46] = (x5 AND NOT x4) AND X`` does.  So
    look for that factorisation directly: for every pair A, B in the span, test
    whether ``(A AND B) XOR target`` is also in the span.
    """
    elems = span_elements(regs)
    member = set(elems)
    piv_all = basis_of(list(regs) + [FULL])
    found = []
    for t in targets:
        if reduce_by(t, piv_all) == 0:
            continue
        for a in elems:
            if a in (0, FULL):
                continue
            at = a & t
            for b in elems:
                if ((a & b) ^ t) in member:
                    p = a & b
                    if p in (0, FULL):
                        continue
                    for k in range(9):
                        trial = list(regs)
                        trial[k] ^= p
                        if reduce_by(t, basis_of(trial + [FULL])) == 0:
                            found.append((p, k, a, b))
                    if found:
                        break
            if found:
                break
    return found


def search(name, code_index, limit, beam=10, max_ands=14, shortlist=300):
    ytrip, xtrip = CODES[code_index]
    triple = ytrip if name in ('u1', 'u2') else xtrip
    targets = targets_for(name, triple)
    start = (tuple(VARS + [0, 0, 0]), (1, 1, 1, 1, 1, 1, 0, 0, 0), ())
    piv = basis_of(list(start[0]) + [FULL])
    states = [(sum(reduce_by(t, piv).bit_count() for t in targets), 0, start)]
    began = time.time()
    for step in range(max_ands):
        pool = {}
        for _, _, (regs, depths, hist) in states:
            for p, k, a, b in exact_completions(targets, regs):
                nregs = list(regs)
                nregs[k] ^= p
                ndep = list(depths)
                ndep[k] = max(ndep[k], 1 + max(max(depths), 1))
                piv = basis_of(nregs + [FULL])
                sc = sum(reduce_by(t, piv).bit_count() for t in targets)
                pool[tuple(nregs)] = (sc, max(ndep),
                                      (tuple(nregs), tuple(ndep), hist + ((a, b, k),)))
            for score, adep, p, k, a, b in expand(regs, depths, targets):
                nregs = list(regs)
                nregs[k] ^= p
                ndep = list(depths)
                ndep[k] = adep
                key = tuple(nregs)
                entry = (score, max(ndep), (tuple(nregs), tuple(ndep), hist + ((a, b, k),)))
                if key not in pool or pool[key][:2] > entry[:2]:
                    pool[key] = entry
        if not pool:
            return None
        shortlisted = sorted(pool.values(), key=lambda z: (z[0], z[1]))[:shortlist]
        rescored = []
        for score, adep, st in shortlisted:
            exact = coset_weight(targets, st[0])
            # Writing a product over a register that still carries unique
            # information shrinks the span, which the coset weight only notices
            # later.  Rank higher-dimensional states first at equal weight.
            rescored.append((exact, -span_dim(st[0]), adep, st))
        states = sorted(rescored, key=lambda z: z[:3])[:beam]
        states = [(z[0], z[2], z[3]) for z in states]
        best = states[0]
        print(f'{name} code{code_index} ands={step + 1} residual={best[0]} '
              f'and_depth={best[1]} t={time.time() - began:.0f}s', flush=True)
        if best[0] == 0:
            regs, depths, hist = best[2]
            return dict(name=name, code_index=code_index, ands=step + 1,
                        and_depth=best[1], triple=list(triple),
                        hist=[[a, b, k] for a, b, k in hist])
        if time.time() - began > limit:
            print('time limit reached', flush=True)
            return None
    return None


if __name__ == '__main__':
    name = sys.argv[1]
    code_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    limit = float(sys.argv[3]) if len(sys.argv) > 3 else 1200
    outdir = Path(sys.argv[4]) if len(sys.argv) > 4 else Path('artifacts/level_nets')
    result = search(name, code_index, limit)
    if result is None:
        raise SystemExit('no network found within the limit')
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f'net_{name}_c{code_index}.json'
    path.write_text(json.dumps(result, indent=2))
    print('wrote', path)
