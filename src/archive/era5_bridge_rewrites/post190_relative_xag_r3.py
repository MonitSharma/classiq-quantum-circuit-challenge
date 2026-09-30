"""Exact algebraic certificate for the two-goal, three-product residual.

This module avoids successor-state expansion.  It enumerates base products by
their quotient modulo the prefix span, then checks the only two ways a second
product can lower the two-dimensional goal quotient.
"""
from __future__ import annotations
import argparse, json, time
from collections import Counter
from pathlib import Path
import numpy as np

from post190_relative_xag import (affine_library, build_reducer, load_prefix,
                                  reduce_mod_span, _unique_forms)


def product_identity(p, u, v):
    return ((p ^ u) & (p ^ v)) == ((p ^ u) & (u ^ v ^ ((1 << 64) - 1)))


def _reduce_array(values, reducer):
    out = np.asarray(values, dtype=np.uint64).copy()
    for bit, row in reducer:
        out = np.where(((out >> np.uint64(bit)) & np.uint64(1)) != 0,
                       out ^ np.uint64(row), out)
    return out


def r3_certificate(prefix, seconds=120):
    start = time.monotonic(); deadline = start + seconds
    base = tuple(prefix['basis']); goals = tuple(prefix['goals'][i] for i in prefix['missing'])
    base_reducer = build_reducer(base)
    goal_reducer = build_reducer(base + goals)
    qgoals = tuple(reduce_mod_span(g, base_reducer) for g in goals)
    report = dict(status='UNSAT', prefix_hash=prefix['prefix_hash'], affine_rank=len(base),
                  goal_quotients=[hex(x) for x in qgoals], goal_quotient_rank=2,
                  affine_forms=0, unordered_base_pairs=0, distinct_product_truth_tables=0,
                  distinct_nonzero_product_classes=0, g_coset_buckets=0,
                  g_bucket_histogram={}, max_bucket_size=0, base_only_collisions=0,
                  p_w_pairs_checked=0, p_w_g_tests=0, successful_memberships=0,
                  elapsed=None)
    if len(goals) != 2:
        report.update(status='not_applicable', reason='requires two missing goals')
        return report
    f = _unique_forms(affine_library(base)); report['affine_forms'] = len(f)
    products = {}
    pair_count = 0
    for i, (a, am) in enumerate(f):
        for b, bm in f[i:]:
            if time.monotonic() > deadline:
                report.update(status='timeout', unordered_base_pairs=pair_count,
                              elapsed=time.monotonic()-start); return report
            pair_count += 1; p = a & b; rem = reduce_mod_span(p, base_reducer)
            if rem:
                products.setdefault(rem, {'truths': set(), 'pairs': 0})['truths'].add(p)
                products[rem]['pairs'] += 1
    report['unordered_base_pairs'] = pair_count
    report['distinct_product_truth_tables'] = sum(len(v['truths']) for v in products.values())
    report['distinct_nonzero_product_classes'] = len(products)
    buckets = {}
    for rem, entry in products.items():
        buckets.setdefault(reduce_mod_span(rem, goal_reducer), []).append(rem)
    hist = Counter(len(v) for v in buckets.values())
    report['g_coset_buckets'] = len(buckets)
    report['g_bucket_histogram'] = {str(k): v for k, v in sorted(hist.items())}
    report['max_bucket_size'] = max(hist, default=0)
    report['base_only_collisions'] = sum(max(0, len(v)-1) for v in buckets.values())
    # A collision is branch A; it does not by itself prove SAT, so continue.
    forms = np.asarray([x[0] for x in f], dtype=np.uint64)
    pclasses = np.asarray(list(products), dtype=np.uint64)
    targets = (goals[0], goals[1], goals[0] ^ goals[1])
    target_hits = []
    for w in forms:
        if time.monotonic() > deadline:
            report.update(status='timeout', elapsed=time.monotonic()-start); return report
        # L_w = S + wS; multiplication by w is linear over GF(2).
        lw = build_reducer(base + tuple(int(w) & int(s) for s in base))
        pw = _reduce_array(pclasses & w, lw)
        report['p_w_pairs_checked'] += len(pclasses)
        for g in targets:
            report['p_w_g_tests'] += len(pclasses)
            hit = np.flatnonzero(pw == np.uint64(reduce_mod_span(g, lw)))
            if len(hit):
                report['successful_memberships'] += int(len(hit))
                target_hits.append({'w': hex(int(w)), 'g': hex(g), 'count': int(len(hit))})
    report['membership_hits'] = target_hits[:100]
    report['status'] = 'UNSAT' if not report['successful_memberships'] and not report['base_only_collisions'] else 'SAT_or_branch_requires_followup'
    report['elapsed'] = time.monotonic()-start
    return report


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--frontier', required=True)
    ap.add_argument('--side', choices=('x','y'), required=True); ap.add_argument('--index', type=int, default=0)
    ap.add_argument('--seconds', type=float, default=120); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); p = load_prefix(a.frontier, a.index, a.side); r = r3_certificate(p, a.seconds)
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(r, indent=2)); print(json.dumps(r, indent=2))


if __name__ == '__main__': main()
