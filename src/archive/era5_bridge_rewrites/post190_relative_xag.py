"""Prefix-relative exact Boolean residual synthesis.

The Boolean search is deliberately independent of the old NIST product bank:
products are made from every affine function of the current prefix span.  It
uses exact 64-bit truth tables and returns explicit product decompositions so
that a later physical scheduler can choose among equivalent realizations.
"""
from __future__ import annotations
import argparse, hashlib, itertools, json, time
from pathlib import Path

from post190_semantic_register import FULL, INPUTS, contains, pivots, span_key
from post190_degree_rank_bound import targets


def affine_library(span):
    """Return truth table -> coefficient masks for an independent affine basis.

    ``canonical_span`` includes the constant direction.  If a caller supplies
    only a linear basis, add it exactly once; duplicate constant insertion must
    not inflate the coefficient metadata.
    """
    values = tuple(span)
    if FULL not in values:
        values = values + (FULL,)
    result = {0: [0]}
    for i, value in enumerate(values):
        old = list(result.items())
        for truth, masks in old:
            result.setdefault(truth ^ value, []).extend(m | (1 << i) for m in masks)
    const_bit = 1 << len(values)
    old = list(result.items())
    for truth, masks in old:
        result.setdefault(truth ^ FULL, []).extend(m | const_bit for m in masks)
    return result


def build_reducer(span):
    """Build a deterministic high-bit GF(2) reducer for the span."""
    rows = {}
    for value in span:
        x = int(value)
        while x:
            bit = x.bit_length() - 1
            if bit in rows:
                x ^= rows[bit]
            else:
                rows[bit] = x
                break
    return tuple(sorted(rows.items(), reverse=True))


def reduce_mod_span(function, reducer):
    x = int(function)
    for bit, row in reducer:
        if (x >> bit) & 1:
            x ^= row
    return x


def same_coset(a, b, reducer):
    return reduce_mod_span(a ^ b, reducer) == 0


def quotient_rank(span, functions):
    reducer = build_reducer(span)
    return len(pivots(tuple(reduce_mod_span(f, reducer) for f in functions)))


def goal_quotient_classes(span, goals):
    reducer = build_reducer(span)
    return tuple(reduce_mod_span(g, reducer) for g in goals)


def mask_cost(mask):
    return (mask.bit_count(), mask)


def canonical_span(values):
    return span_key(tuple(values))


def load_prefix(path, index=0, side=None):
    data = json.loads(Path(path).read_text())
    entry = data[index] if isinstance(data, list) else data
    clean = tuple(int(v, 16) if isinstance(v, str) else int(v) for v in entry['clean_values'])
    full = tuple(int(v, 16) if isinstance(v, str) else int(v) for v in entry.get('full_values', []))
    if len(full) != 9:
        full = None
    if side is None:
        side = 'y' if 'quotient_y' in str(path) or '/y' in str(path) else 'x'
    goal_table = tuple(sum(1 << x for x in range(64) if bit[x])
                       for bit in targets()[side])
    raw = INPUTS[5] if side == 'y' else INPUTS[4] ^ INPUTS[5]
    goals = goal_table + (raw,)
    basis = canonical_span(clean)
    p = pivots((FULL, *clean))
    present = tuple(i for i, g in enumerate(goals) if contains(p, g))
    missing = tuple(i for i in range(len(goals)) if i not in present)
    return dict(source=str(path), index=index, side=side, clean=clean, full=full,
                basis=basis, goals=goals, present=present, missing=missing,
                times=entry.get('times'), ops=entry.get('ops'),
                prefix_depth=max(entry.get('times', [0])),
                prefix_hash=hashlib.sha256(Path(path).read_bytes()).hexdigest())


def _products(library, deadline):
    """Enumerate unique nonconstant products and retain diverse decompositions."""
    forms = sorted((t, min(ms, key=mask_cost)) for t, ms in library.items())
    out = {}
    for ai, (a, am) in enumerate(forms):
        if time.monotonic() > deadline:
            return out, True
        for b, bm in forms[ai:]:
            if time.monotonic() > deadline:
                return out, True
            if am == bm or not a or not b:
                continue
            g = a & b
            if g in library:
                continue
            pair = (am, bm) if am < bm else (bm, am)
            cur = out.get(g)
            if cur is None:
                out[g] = [pair]
            elif len(cur) < 8 and pair not in cur:
                cur.append(pair)
    return out, False


def residual_search(prefix, max_products=2, max_stages=2, seconds=30):
    """Exhaustively solve small residual bounds, or return an explicit timeout."""
    start = time.monotonic(); deadline = start + seconds
    base = tuple(prefix['basis'])
    goals = tuple(prefix['goals'][i] for i in prefix['missing'])
    if not goals:
        return dict(status='SAT', products=0, stages=0, gates=[], checked_states=1)
    if all(contains(pivots((FULL, *base)), g) for g in goals):
        return dict(status='SAT', products=0, stages=0, gates=[], checked_states=1)
    frontier = {canonical_span(base): (base, [], 0)}
    checked = 0
    for gates in range(max_products + 1):
        next_frontier = {}
        for key, (span, recipe, stage) in frontier.items():
            checked += 1
            pp = pivots((FULL, *span))
            if all(contains(pp, g) for g in goals):
                return dict(status='SAT', products=gates, stages=stage,
                            gates=recipe, checked_states=checked,
                            elapsed=time.monotonic()-start)
            if gates == max_products or time.monotonic() > deadline:
                continue
            lib = affine_library(span)
            products, timed = _products(lib, deadline)
            if timed:
                return dict(status='timeout', products_checked=gates,
                            checked_states=checked, elapsed=time.monotonic()-start)
            for product, decomps in products.items():
                # A product which does not enlarge the span cannot help here.
                if product in span:
                    continue
                # Product truth functions are semantic states; preserve several
                # operand masks for the later physical phase.
                ns = tuple(span) + (product,)
                nkey = canonical_span(ns)
                nstage = stage + 1
                if nstage > max_stages:
                    continue
                old = next_frontier.get(nkey)
                if old is None or nstage < old[2]:
                    next_frontier[nkey] = (ns, recipe + [{'product': hex(product),
                        'operands': [[hex(x), hex(y)] for x, y in decomps],
                        'stage': nstage}], nstage)
        if time.monotonic() > deadline:
            return dict(status='timeout', products_checked=gates,
                        checked_states=checked, elapsed=time.monotonic()-start)
        frontier = next_frontier
        if not frontier:
            break
    return dict(status='UNSAT', max_products=max_products,
                max_stages=max_stages, checked_states=checked,
                elapsed=time.monotonic()-start)


def _unique_forms(library):
    return sorted((truth, min(masks, key=mask_cost)) for truth, masks in library.items())


def _product_pass(forms, reducer, useful=None, deadline=None, keep=16):
    products = {}
    examined = 0
    in_span = 0
    distinct = set()
    for i, (a, am) in enumerate(forms):
        for b, bm in forms[i:]:
            examined += 1
            if deadline is not None and time.monotonic() > deadline:
                return products, dict(status='timeout', pairs_examined=examined,
                                      in_span=in_span, distinct_products=len(distinct))
            product = a & b
            rem = reduce_mod_span(product, reducer)
            if rem == 0:
                in_span += 1
                continue
            distinct.add(product)
            if useful is not None and rem not in useful:
                continue
            entry = products.setdefault(rem, {'products': {}, 'decompositions': 0})
            entry['decompositions'] += 1
            entry['products'].setdefault(product, []).append((am, bm))
            # Keep all distinct truth-table representatives, but cap aliases.
            for product_aliases in entry['products'].values():
                if len(product_aliases) > keep:
                    del product_aliases[keep:]
    return products, dict(status='complete', pairs_examined=examined,
                          in_span=in_span, distinct_products=len(distinct))


def residual_search_r2_exact(prefix, seconds=120, keep=16):
    """Settle the two-product residual using the exact three-class quotient.

    This never materializes one state per first product.  A finite completion
    is UNSAT only when all useful quotient branches and their second-product
    pair spaces have been exhausted.
    """
    start = time.monotonic(); deadline = start + seconds
    base = tuple(prefix['basis'])
    missing = tuple(prefix['goals'][i] for i in prefix['missing'])
    base_reducer = build_reducer(base)
    qgoals = tuple(reduce_mod_span(g, base_reducer) for g in missing)
    qrank = len(pivots(qgoals))
    report = dict(status='UNSAT', quotient_rank=qrank, goal_quotients=[hex(x) for x in qgoals],
                  useful_classes=[], base_forms=0, first_pairs_examined=0,
                  first_distinct_products=0, second_pairs_examined=0,
                  elapsed=None)
    if len(missing) != 2:
        report.update(status='not_applicable', reason='requires exactly two missing goals')
        return report
    if qrank != 2:
        report.update(status='not_applicable', reason='quotient theorem branch assumes rank 2')
        return report
    q1, q2 = qgoals
    useful = {q1, q2, q1 ^ q2}
    f0 = _unique_forms(affine_library(base))
    report['base_forms'] = len(f0)
    first, first_metrics = _product_pass(f0, base_reducer, useful, deadline, keep)
    report['first_pairs_examined'] = first_metrics['pairs_examined']
    report['first_distinct_products'] = first_metrics['distinct_products']
    if first_metrics['status'] == 'timeout':
        report.update(status='timeout', elapsed=time.monotonic()-start)
        return report
    for qclass in sorted(first):
        if time.monotonic() > deadline:
            report.update(status='timeout', elapsed=time.monotonic()-start)
            return report
        # One representative is semantically sufficient; aliases are metadata.
        ptruth = next(iter(first[qclass]['products']))
        s1 = tuple(canonical_span(base + (ptruth,)))
        r1 = build_reducer(s1)
        required = reduce_mod_span(q2 if qclass == q1 else q1 if qclass == q2 else q1,
                                   r1)
        f1 = sorted(f0 + [(truth ^ ptruth, mask | (1 << len(base)))
                          for truth, mask in f0])
        second, second_metrics = _product_pass(f1, r1, {required}, deadline, keep)
        branch = dict(classification=hex(qclass), concrete_first_products=len(first[qclass]['products']),
                      first_decompositions=first[qclass]['decompositions'],
                      second_forms=len(f1), second_pairs_examined=second_metrics['pairs_examined'],
                      second_status=second_metrics['status'], required=hex(required),
                      second_products=len(second.get(required, {}).get('products', {})))
        report['useful_classes'].append(branch)
        report['second_pairs_examined'] += second_metrics['pairs_examined']
        if second_metrics['status'] == 'timeout':
            report.update(status='timeout', elapsed=time.monotonic()-start)
            return report
        if required in second:
            p2truth, p2aliases = next(iter(second[required]['products'].items()))
            p1aliases = first[qclass]['products'][ptruth]
            gates = [{'product': hex(ptruth), 'operands': [[hex(a), hex(b)] for a,b in p1aliases], 'stage': 1},
                     {'product': hex(p2truth), 'operands': [[hex(a), hex(b)] for a,b in p2aliases], 'stage': 2}]
            same_stage = sum(not ((a >> len(base)) & 1 or (b >> len(base)) & 1)
                             for a, b in p2aliases)
            report.update(status='SAT', gates=gates, same_stage_decompositions=same_stage,
                          dependent_decompositions=len(p2aliases)-same_stage,
                          stages=1 if same_stage else 2, elapsed=time.monotonic()-start)
            return report
    report['elapsed'] = time.monotonic()-start
    return report


def portfolio(frontier_paths, side, seconds_each=5, limit=None):
    rows = []
    for path in frontier_paths[:limit]:
        prefix = load_prefix(path, side=side)
        r = residual_search(prefix, max_products=2, max_stages=2, seconds=seconds_each)
        rows.append(dict(source=str(path), index=prefix['index'], side=side,
                         prefix_depth=prefix['prefix_depth'], present=prefix['present'],
                         clean_rank=len(prefix['basis']), result=r))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frontier', action='append', required=True)
    ap.add_argument('--side', choices=['x','y'], required=True)
    ap.add_argument('--index', type=int, default=0)
    ap.add_argument('--seconds', type=float, default=30)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); a.out.parent.mkdir(parents=True, exist_ok=True)
    prefixes = [load_prefix(p, a.index, a.side) for p in a.frontier]
    reports = []
    for prefix in prefixes:
        r = residual_search(prefix, max_products=3, max_stages=3, seconds=a.seconds)
        reports.append({'prefix': {k: v for k, v in prefix.items() if k not in ('full','clean')},
                        'result': r})
    a.out.write_text(json.dumps(reports, indent=2))
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()
