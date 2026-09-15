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
    """Return truth table -> all coefficient masks (bit 0..n-1, constant n)."""
    values = tuple(span)
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
