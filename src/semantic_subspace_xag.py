"""Subspace-quotiented shared-XAG search at analytic minimum bounds.

Truth signatures are 64-bit integers.  A search state is a canonical GF(2)
span of available signatures, so affine-expression syntax is quotient-ed out.
The search is deliberately bounded: an unresolved result is reported as such,
never as a lower bound.
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

from radius import R, radius
from search import truth


FULL = (1 << 64) - 1
INPUTS = [sum(1 << row for row in range(64) if row & (1 << bit)) for bit in range(6)]
FEATURES = {
    "R0": R[0], "R1": R[1], "R2": R[2],
    "A": truth(range(29, 54)), "B": truth(range(39, 44)),
    "V": truth(y for y in range(64) if radius(y) > 0),
}


def insert(basis, value):
    """Insert and return a reduced pivot dictionary keyed by highest bit."""
    rows = dict(basis)
    value = reduce_span(value, rows)
    if not value:
        return rows
    pivot = value.bit_length() - 1
    for p, row in list(rows.items()):
        if row & (1 << pivot):
            rows[p] = row ^ value
    rows[pivot] = value
    return dict(sorted(rows.items(), reverse=True))


def reduce_span(value, basis):
    for pivot, row in sorted(basis.items(), reverse=True):
        if value & (1 << pivot):
            value ^= row
    return value


def canonical(basis):
    return tuple(basis[p] for p in sorted(basis, reverse=True))


def as_basis(key):
    return {row.bit_length() - 1: row for row in key}


def span_elements(key):
    values = [0]
    for row in key:
        values += [x ^ row for x in values]
    return values


def quotient_rank(targets, key):
    basis = as_basis(key)
    work = dict(basis)
    before = len(work)
    for target in targets:
        work = insert(work, target)
    return len(work) - before


def anf_high_signature(table, min_degree=5):
    coefficients = [(table >> i) & 1 for i in range(64)]
    for bit in range(6):
        for mask in range(64):
            if mask & (1 << bit):
                coefficients[mask] ^= coefficients[mask ^ (1 << bit)]
    return sum(1 << mask for mask, value in enumerate(coefficients)
               if value and mask.bit_count() >= min_degree)


def gf2_rank(values):
    basis = {}
    for value in values:
        reduced = reduce_span(value, basis)
        if reduced:
            basis[reduced.bit_length() - 1] = reduced
    return len(basis)


def high_degree_report(names):
    high = [anf_high_signature(FEATURES[name]) for name in names]
    monomials = {name: [mask for mask in range(64)
                        if high[i] >> mask & 1]
                 for i, name in enumerate(names)}
    rank = gf2_rank(high)
    return {"features": list(names), "high_degree_monomials": monomials,
            "high_degree_rank": rank, "and_lower_bound": 2 + rank}


def search_minimum(targets, minimum, timeout_seconds=30.0, max_states=20000):
    started = time.time()
    initial_basis = {}
    for signal in [FULL, *INPUTS]:
        initial_basis = insert(initial_basis, signal)
    initial = canonical(initial_basis)
    frontier = {initial: []}
    visited = {initial}
    stats = []
    for depth in range(minimum):
        next_frontier = {}
        extensions = 0
        for key, witness in frontier.items():
            if time.time() - started > timeout_seconds:
                return {"status": "timeout", "depth_reached": depth,
                        "states": len(visited), "extensions": extensions,
                        "elapsed_seconds": time.time() - started}
            basis = as_basis(key)
            values = span_elements(key)
            products = {}
            for i, left in enumerate(values):
                for right in values[i:]:
                    product = reduce_span(left & right, basis)
                    if product:
                        products.setdefault(product, (left, right))
            for product, factors in products.items():
                child = canonical(insert(basis, product))
                if child in visited:
                    continue
                remaining = minimum - depth - 1
                if quotient_rank(targets, child) > remaining:
                    continue
                visited.add(child)
                next_frontier[child] = witness + [{"left": factors[0], "right": factors[1],
                                                   "signature": product}]
                extensions += 1
                if len(visited) >= max_states:
                    return {"status": "state_limit", "depth_reached": depth + 1,
                            "states": len(visited), "extensions": extensions,
                            "elapsed_seconds": time.time() - started}
        stats.append({"depth": depth + 1, "frontier": len(next_frontier),
                      "states": len(visited), "extensions": extensions})
        frontier = next_frontier
        if not frontier:
            return {"status": "no_solution_at_bound", "depth_reached": depth + 1,
                    "states": len(visited), "stats": stats,
                    "elapsed_seconds": time.time() - started}
    for key, witness in frontier.items():
        if all(reduce_span(target, as_basis(key)) == 0 for target in targets):
            return {"status": "exact", "and_count": minimum, "witness": witness,
                    "states": len(visited), "stats": stats,
                    "elapsed_seconds": time.time() - started}
    return {"status": "no_solution_at_bound", "depth_reached": minimum,
            "states": len(visited), "stats": stats,
            "elapsed_seconds": time.time() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-states", type=int, default=20000)
    args = parser.parse_args()
    groups = [("R0", "R1"), ("R1", "R2"), ("A", "B"), ("A", "B", "V")]
    rows = []
    for names in groups:
        bound = high_degree_report(names)
        print("searching", names, "at", bound["and_lower_bound"], "ANDs", flush=True)
        result = search_minimum([FEATURES[name] for name in names], bound["and_lower_bound"],
                                args.timeout, args.max_states)
        rows.append({**bound, "search": result})
    report = {"backend": "gf2_span_quotiented_shared_xag", "rows": rows}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
