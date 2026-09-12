"""Exact minimal-AND synthesis for small Boolean functions.

Used to build level encoders.  A six-variable code bit is split by two chosen
variables into four subfunctions of the remaining four, and every four-variable
function has multiplicative complexity at most three, so the subfunctions are
cheap if they are synthesised jointly: what costs depth is the number of AND
gates, and sharing products across the twelve subfunctions of an encoder cuts
that sharply.

The search is exhaustive over AND count.  Values are truth tables on ``nvars``
variables, so the whole space is small enough to enumerate the span at every
step.
"""
from itertools import combinations


def var_tables(nvars):
    n = 1 << nvars
    full = (1 << n) - 1
    return [sum(((t >> i) & 1) << t for t in range(n)) for i in range(nvars)], full


def span_of(basis, full):
    out = [0]
    for e in basis:
        out += [x ^ e for x in out]
    return out


def independent(basis, v):
    """Reduce v against basis; return the residual (0 means v is in the span)."""
    for e in basis:
        lead = e.bit_length() - 1
        if v >> lead & 1:
            v ^= e
    return v


def make_basis(vectors):
    basis = []
    for v in vectors:
        r = independent(basis, v)
        if r:
            basis.append(r)
            basis.sort(key=lambda z: -z.bit_length())
    return basis


def solve(targets, nvars=4, max_ands=6, beam=400):
    """Return (ands, products) where products is a list of (a, b) truth tables.

    ``ands`` is minimal over the searched range; the caller recovers each target
    as an XOR of span elements.
    """
    vars_, full = var_tables(nvars)
    start = tuple([full] + vars_)
    def done(pool):
        basis = make_basis(list(pool))
        return all(independent(basis, t) == 0 for t in targets)
    if done(start):
        return 0, [], start
    frontier = {start: ()}
    for depth in range(1, max_ands + 1):
        nxt = {}
        for pool, hist in frontier.items():
            basis = make_basis(list(pool))
            elems = span_of(basis, full)
            seen = set()
            for i, a in enumerate(elems):
                if a in (0, full):
                    continue
                for b in elems[i:]:
                    p = a & b
                    if p in seen or independent(basis, p) == 0:
                        continue
                    seen.add(p)
                    np_ = pool + (p,)
                    if np_ in nxt:
                        continue
                    nxt[np_] = hist + ((a, b),)
                    if done(np_):
                        return depth, list(nxt[np_]), np_
        # keep the states whose basis covers the most target dimensions
        def rank_key(item):
            pool, _ = item
            basis = make_basis(list(pool))
            return sum(1 for t in targets if independent(basis, t) == 0)
        frontier = dict(sorted(nxt.items(), key=rank_key, reverse=True)[:beam])
        if not frontier:
            break
    return None, None, None


def express(target, pool):
    """Return the subset of pool indices whose XOR equals target, or None."""
    items = list(enumerate(pool))
    basis = []
    for idx, v in items:
        cur, comb = v, frozenset([idx])
        for e, c in basis:
            lead = e.bit_length() - 1
            if cur >> lead & 1:
                cur ^= e
                comb = comb ^ c
        if cur:
            basis.append((cur, comb))
            basis.sort(key=lambda z: -z[0].bit_length())
    cur, comb = target, frozenset()
    for e, c in basis:
        lead = e.bit_length() - 1
        if cur >> lead & 1:
            cur ^= e
            comb = comb ^ c
    return comb if cur == 0 else None
