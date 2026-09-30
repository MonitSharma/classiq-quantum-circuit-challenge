"""Build level encoders as AND networks instead of multiplexers.

A six-variable code bit splits on two chosen variables into four subfunctions of
the remaining four:

    h = A XOR v1.B XOR v0.C XOR (v1 AND v0).D

Every four-variable function has multiplicative complexity at most three, and
the twelve subfunctions of an encoder share products heavily, so the four-
variable part is synthesised jointly by ``mc_small.solve``.  What is left is the
combining ANDs, at most three per code bit plus one for ``v1 AND v0``.

The result is a list of ``(a, b, k)`` triples - multiply the truth tables ``a``
and ``b`` and XOR the product into register ``k`` - which is exactly what
``level_oracle.emit_encoder`` replays.
"""
import itertools

from mc_small import solve, express, make_basis, independent

FULL = (1 << 64) - 1
VARS6 = [sum(((t >> i) & 1) << t for t in range(64)) for i in range(6)]


def _rng(a, b):
    return set(range(a, b + 1))


NESTED = {
    'u1': [_rng(11, 27), _rng(12, 26), _rng(13, 25), _rng(15, 23), _rng(17, 21)],
    'v1': [_rng(32, 48), _rng(33, 47), _rng(34, 46), _rng(36, 44), _rng(38, 42)],
    'u2': [_rng(29, 53), _rng(35, 47), _rng(36, 46), _rng(37, 45), _rng(39, 43)],
    'v2': [_rng(2, 61), _rng(2, 26) | _rng(50, 60), _rng(2, 26) | _rng(51, 59),
           _rng(2, 26) | _rng(53, 57), _rng(2, 26)],
}
LEVEL = {k: [sum(1 for s in v if t in s) for t in range(64)] for k, v in NESTED.items()}


def code_targets(name, triple):
    """The three six-variable code-bit truth tables."""
    lv = LEVEL[name]
    return [sum(1 << t for t in range(64) if (sub >> lv[t]) & 1) for sub in triple]


def quadrant_parts(tt, hi, lo):
    """Reed-Muller parts A, B, C, D as 16-bit tables over the four low variables."""
    p, q = hi
    subs = [0, 0, 0, 0]
    for t in range(64):
        if not (tt >> t) & 1:
            continue
        qi = (((t >> p) & 1) << 1) | ((t >> q) & 1)
        low = 0
        for k, v in enumerate(lo):
            low |= ((t >> v) & 1) << k
        subs[qi] |= 1 << low
    f00, f01, f10, f11 = subs
    return f00, f00 ^ f01, f00 ^ f10, f00 ^ f01 ^ f10 ^ f11


def lift(table16, lo):
    """Lift a 16-bit table over the low variables back to a 64-bit table."""
    out = 0
    for t in range(64):
        low = 0
        for k, v in enumerate(lo):
            low |= ((t >> v) & 1) << k
        if (table16 >> low) & 1:
            out |= 1 << t
    return out


def plan(name, triple, hi, max_ands=6, beam=250):
    """Return (four_var_products, parts) for this encoder, or None."""
    lo = [v for v in range(6) if v not in hi]
    targets = code_targets(name, triple)
    parts = [quadrant_parts(t, hi, lo) for t in targets]
    wanted = sorted({v for p in parts for v in p if v not in (0, 0xFFFF)})
    ands, prods, pool = solve(wanted, 4, max_ands=max_ands, beam=beam)
    if ands is None:
        return None
    return dict(lo=lo, hi=hi, parts=parts, prods=prods, pool=pool,
                four_var_ands=ands, targets=targets)


def and_count(p):
    """Total ANDs: four-variable network plus combining."""
    combine = 0
    need_hi_product = False
    for A, B, C, D in p['parts']:
        for v, kind in ((B, 'B'), (C, 'C'), (D, 'D')):
            if v not in (0,):
                combine += 1
                if kind == 'D':
                    need_hi_product = True
    return p['four_var_ands'] + combine + (1 if need_hi_product else 0)


def best_split(name, triple, max_ands=6, beam=200, splits=None):
    best = None
    for hi in (splits or list(itertools.combinations(range(6), 2))):
        p = plan(name, triple, hi, max_ands=max_ands, beam=beam)
        if p is None:
            continue
        n = and_count(p)
        if best is None or n < best[0]:
            best = (n, p)
    return best


# ---------------------------------------------------------------- network build
def _basis64(vals):
    piv = {}
    for v in vals:
        for b in range(63, -1, -1):
            if v >> b & 1:
                if b in piv:
                    v ^= piv[b]
                else:
                    piv[b] = v
                    break
    return piv


def _in_span(v, piv):
    for b in range(63, -1, -1):
        if v >> b & 1 and b in piv:
            v ^= piv[b]
    return v == 0


def op_list(plan_d, triple, name):
    """Ordered (a, b) products: the four-variable network then the combining ANDs.

    Combining uses the nested form ``h = A XOR q.(B XOR p.D) XOR p.C`` so no
    register is spent on ``p AND q``.
    """
    lo, hi = plan_d['lo'], plan_d['hi']
    p_var, q_var = VARS6[hi[0]], VARS6[hi[1]]
    ops = []
    for a16, b16 in plan_d['prods']:
        ops.append((lift(a16, lo), lift(b16, lo)))
    # value produced by each four-variable product, for bookkeeping
    four_var = list(ops)
    # Accumulate every combining product straight into the code bit's register,
    # so no register is spent on a per-bit intermediate.  That needs p AND q as
    # a shared value, which costs one AND but saves three registers.
    need_h = any(lift(D, lo) for _, _, _, D in plan_d['parts'])
    h_val = p_var & q_var
    if need_h:
        ops.append((p_var, q_var))
    for A, B, C, D in plan_d['parts']:
        A64, B64, C64, D64 = (lift(v, lo) for v in (A, B, C, D))
        if B64:
            ops.append((q_var, B64))
        if C64:
            ops.append((p_var, C64))
        if D64:
            ops.append((h_val, D64))
    # Re-apply the four-variable products at the end.  Nine registers hold only
    # ten dimensions, so the products have to be cleared before the code bits
    # can occupy their slots; re-running the same RCCX cancels them.
    ops.extend(reversed(four_var))
    return ops


def allocate(ops, targets, nregs=9):
    """Assign a target register to each product, keeping every later need in span.

    Returns the (a, b, k) history or None if no greedy assignment works.
    """
    regs = list(VARS6) + [0] * (nregs - 6)
    hist = []
    future = []
    acc = set()
    for i in range(len(ops) - 1, -1, -1):
        future.append(frozenset(acc))
        acc = set(acc) | {ops[i][0], ops[i][1]}
    future.reverse()
    for i, (a, b) in enumerate(ops):
        piv = _basis64(regs + [FULL])
        if not (_in_span(a, piv) and _in_span(b, piv)):
            return None
        p = a & b
        need = future[i]
        placed = False
        for k in list(range(6, nregs)) + list(range(6)):
            trial = list(regs)
            trial[k] ^= p
            tpiv = _basis64(trial + [FULL])
            if all(_in_span(v, tpiv) for v in need) and _in_span(a, tpiv) and _in_span(b, tpiv):
                regs = trial
                hist.append((a, b, k))
                placed = True
                break
        if not placed:
            return None
    piv = _basis64(regs + [FULL])
    if not all(_in_span(t, piv) for t in targets):
        return None
    return hist


def allocate_search(ops, targets, nregs=9, tries=4000, seed=0):
    """Randomised allocation: choose both the order of products and their targets.

    Nine registers hold at most ten dimensions with the constant, and the six
    inputs already use seven, so only three nonlinear values are live at once.
    A product may therefore have to be written over another one, which is legal
    only while every value still needed stays in the span.  Greedy ordering
    fails; searching over orders does not.
    """
    import random
    rng = random.Random(seed)
    n = len(ops)
    for _ in range(tries):
        regs = list(VARS6) + [0] * (nregs - 6)
        remaining = list(range(n))
        hist = []
        ok = True
        while remaining:
            piv = _basis64(regs + [FULL])
            ready = [i for i in remaining
                     if _in_span(ops[i][0], piv) and _in_span(ops[i][1], piv)]
            if not ready:
                ok = False
                break
            rng.shuffle(ready)
            moved = False
            for i in ready:
                a, b = ops[i]
                p = a & b
                # Only protect values we already have and still need; later
                # operands that do not exist yet cannot be required to survive.
                need = {v for j in remaining if j != i for v in ops[j]
                        if _in_span(v, piv)}
                # Once a code bit becomes reachable, never lose it again.
                need |= {t for t in targets if _in_span(t, piv)}
                order = list(range(nregs))
                rng.shuffle(order)
                for k in order:
                    trial = list(regs)
                    trial[k] ^= p
                    tp = _basis64(trial + [FULL])
                    if all(_in_span(v, tp) for v in need):
                        regs = trial
                        hist.append((a, b, k))
                        remaining.remove(i)
                        moved = True
                        break
                if moved:
                    break
            if not moved:
                ok = False
                break
        if ok:
            piv = _basis64(regs + [FULL])
            if all(_in_span(t, piv) for t in targets):
                return hist
    return None


def allocate_joint(ops_y, targets_y, ops_x, targets_x, nanc=6, tries=3000, seed=0):
    """Allocate both encoders against one shared pool of ancillas.

    Each side alone has only three spare nonlinear dimensions, which is too few:
    the four-variable products and the combining products cannot all be live.
    But the six ancillas are a shared pool, so while one side is at its peak the
    other can be using fewer.  This searches for an interleaving that keeps both
    sides feasible, and returns per-side histories over nine logical registers
    (six data wires then the ancillas assigned to that side).
    """
    import random
    rng = random.Random(seed)

    def fresh(ops, targets):
        return dict(ops=list(ops), targets=list(targets), regs=list(VARS6),
                    anc=[], hist=[], left=list(range(len(ops))))

    for _ in range(tries):
        sides = [fresh(ops_y, targets_y), fresh(ops_x, targets_x)]
        free = list(range(nanc))
        ok = True
        while any(s['left'] for s in sides):
            progressed = False
            for s in rng.sample(sides, 2):
                if not s['left']:
                    continue
                regs = s['regs'] + [0] * 0
                piv = _basis64(regs + [FULL])
                ready = [i for i in s['left']
                         if _in_span(s['ops'][i][0], piv) and _in_span(s['ops'][i][1], piv)]
                rng.shuffle(ready)
                for i in ready:
                    a, b = s['ops'][i]
                    p = a & b
                    need = {v for j in s['left'] if j != i for v in s['ops'][j]
                            if _in_span(v, piv)}
                    need |= {t for t in s['targets'] if _in_span(t, piv)}
                    slots = list(range(len(regs)))
                    rng.shuffle(slots)
                    if free:
                        slots = [len(regs)] + slots   # option: take a new ancilla
                    done = False
                    for k in slots:
                        if k == len(regs):
                            trial = regs + [p]
                        else:
                            trial = list(regs)
                            trial[k] ^= p
                        tp = _basis64(trial + [FULL])
                        if all(_in_span(v, tp) for v in need):
                            if k == len(regs):
                                s['anc'].append(free.pop(0))
                            s['regs'] = trial
                            s['hist'].append((a, b, k))
                            s['left'].remove(i)
                            done = True
                            break
                    if done:
                        progressed = True
                        break
                if progressed:
                    break
            if not progressed:
                ok = False
                break
        if not ok:
            continue
        good = True
        for s in sides:
            piv = _basis64(s['regs'] + [FULL])
            if not all(_in_span(t, piv) for t in s['targets']):
                good = False
        if good:
            return sides
    return None


def small_decompose(value, regs, avoid=()):
    """Shortest register combination (with optional constant) whose XOR is value."""
    idx = [i for i in range(len(regs)) if i not in avoid]
    for const in (False, True):
        v = value ^ (FULL if const else 0)
        if v == 0:
            return frozenset([-1] if const else [])
        for i in idx:
            if regs[i] == v:
                return frozenset([i] + ([-1] if const else []))
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                if regs[idx[a]] ^ regs[idx[b]] == v:
                    return frozenset([idx[a], idx[b]] + ([-1] if const else []))
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                for c in range(b + 1, len(idx)):
                    if regs[idx[a]] ^ regs[idx[b]] ^ regs[idx[c]] == v:
                        return frozenset([idx[a], idx[b], idx[c]] + ([-1] if const else []))
    # fall back to Gaussian elimination
    items = [(i, regs[i]) for i in idx] + [(-1, FULL)]
    piv = {}
    for i, v in items:
        cur, comb = v, frozenset([i])
        for b in range(63, -1, -1):
            if cur >> b & 1:
                if b in piv:
                    pv, pc = piv[b]
                    cur ^= pv
                    comb = comb ^ pc
                else:
                    piv[b] = (cur, comb)
                    break
    cur, comb = value, frozenset()
    for b in range(63, -1, -1):
        if cur >> b & 1:
            if b not in piv:
                return None
            pv, pc = piv[b]
            cur ^= pv
            comb = comb ^ pc
    return comb if cur == 0 else None


def emit_network(qc, hist, wires, targets, slots, nregs):
    """Replay an AND network on ``wires`` and leave ``targets`` on ``slots``."""
    regs = list(VARS6) + [0] * (nregs - 6)
    for a, b, k in hist:
        used = {k}
        prep = []
        for val in (a, b):
            comb = small_decompose(val, regs, avoid=used)
            assert comb is not None, 'operand outside register span'
            neg = -1 in comb
            idxs = sorted(i for i in comb if i != -1)
            assert idxs, 'operand is constant'
            host = next((i for i in idxs if i not in used), None)
            assert host is not None, 'no free host wire'
            used.add(host)
            rest = [i for i in idxs if i != host]
            for i in rest:
                qc.cx(wires[i], wires[host])
                regs[host] ^= regs[i]
            if neg:
                qc.x(wires[host])
                regs[host] ^= FULL
            prep.append((host, rest, neg))
        (ha, _, _), (hb, _, _) = prep
        qc.rccx(wires[ha], wires[hb], wires[k])
        regs[k] ^= regs[ha] & regs[hb]
        for host, rest, neg in reversed(prep):
            if neg:
                qc.x(wires[host])
                regs[host] ^= FULL
            for i in reversed(rest):
                qc.cx(wires[i], wires[host])
                regs[host] ^= regs[i]
    for slot, tgt in zip(slots, targets):
        comb = small_decompose(tgt ^ regs[slot], regs, avoid=())
        assert comb is not None, 'target outside register span'
        for i in sorted(comb):
            if i == -1:
                qc.x(wires[slot])
                regs[slot] ^= FULL
            else:
                assert i != slot, 'self-reference placing a code bit'
                qc.cx(wires[i], wires[slot])
                regs[slot] ^= regs[i]
    for slot, tgt in zip(slots, targets):
        assert regs[slot] == tgt, 'code placement failed'
    return regs
