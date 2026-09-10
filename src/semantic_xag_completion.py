"""Candidate-mode exact completion for minimum shared-XAGs.

The first two AND extensions are enumerated one span at a time.  Remaining
target quotient directions are solved by provenance-tracked Gaussian
elimination, avoiding a global layer-two frontier.
"""
from __future__ import annotations

import argparse
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


def reduce_value(value, basis):
    for pivot, row in sorted(basis.items(), reverse=True):
        if value & (1 << pivot):
            value ^= row
    return value


def insert(basis, value):
    rows = dict(basis)
    value = reduce_value(value, rows)
    if not value:
        return rows
    pivot = value.bit_length() - 1
    for p, row in list(rows.items()):
        if row & (1 << pivot):
            rows[p] = row ^ value
    rows[pivot] = value
    return dict(sorted(rows.items(), reverse=True))


def canonical(basis):
    return tuple(basis[p] for p in sorted(basis, reverse=True))


def as_basis(key):
    return {row.bit_length() - 1: row for row in key}


def span_elements(key):
    values = [0]
    for row in key:
        values += [x ^ row for x in values]
    return values


def initial_key():
    basis = {}
    for signal in [FULL, *INPUTS]:
        basis = insert(basis, signal)
    return canonical(basis)


def product_extensions(key):
    basis = as_basis(key)
    values = span_elements(key)
    products = {}
    for i, left in enumerate(values):
        for right in values[i:]:
            product = reduce_value(left & right, basis)
            if product:
                products.setdefault(product, (left, right))
    return products


def target_quotient_basis(targets, key):
    basis = as_basis(key)
    quotient = {}
    for target in targets:
        residual = reduce_value(target, basis)
        if residual:
            pivot = residual.bit_length() - 1
            for p, row in list(quotient.items()):
                if row & (1 << pivot):
                    quotient[p] = row ^ residual
            quotient[pivot] = residual
    return list(quotient.values())


def nonzero_directions(quotient_basis):
    rows = list(quotient_basis)
    directions = []
    for mask in range(1, 1 << len(rows)):
        value = 0
        for i, row in enumerate(rows):
            if mask >> i & 1:
                value ^= row
        directions.append(value)
    return directions


def find_product_in_coset(key, direction):
    """Find f,g in span(key) with f&g == direction modulo span(key)."""
    basis = as_basis(key)
    basis_rows = list(key)
    values = span_elements(key)
    for f in values:
        generators = list(basis_rows)
        generators.extend(f & row for row in basis_rows)
        rows = {}
        provenance = {}
        for index, generator in enumerate(generators):
            value = generator
            coeff = 1 << index
            for pivot in sorted(rows, reverse=True):
                if value & (1 << pivot):
                    value ^= rows[pivot]
                    coeff ^= provenance[pivot]
            if not value:
                continue
            pivot = value.bit_length() - 1
            for p in list(rows):
                if rows[p] & (1 << pivot):
                    rows[p] ^= value
                    provenance[p] ^= coeff
            rows[pivot] = value
            provenance[pivot] = coeff
        value = direction
        coeff = 0
        for pivot in sorted(rows, reverse=True):
            if value & (1 << pivot):
                value ^= rows[pivot]
                coeff ^= provenance[pivot]
        if value == 0:
            g = 0
            for j, row in enumerate(basis_rows):
                if coeff >> (len(basis_rows) + j) & 1:
                    g ^= row
            if g:
                actual = f & g
                return {"left": f, "right": g, "actual_product": actual,
                        "quotient_direction": direction,
                        "affine_correction": actual ^ direction}
    return None


def search_pair(names, timeout_seconds=60.0, max_first=10000, max_second=None):
    started = time.time()
    targets = [FEATURES[name] for name in names]
    s0 = initial_key()
    firsts = product_extensions(s0)
    counters = {"first_extensions": len(firsts), "second_extensions": 0,
                "direction_tests": 0, "completion_successes": 0}
    for first_index, (a1, witness1) in enumerate(firsts.items()):
        if first_index >= max_first or time.time() - started > timeout_seconds:
            break
        s1 = canonical(insert(as_basis(s0), a1))
        for a2, witness2 in product_extensions(s1).items():
            counters["second_extensions"] += 1
            s2 = canonical(insert(as_basis(s1), a2))
            quotient_basis = target_quotient_basis(targets, s2)
            if len(quotient_basis) != 2:
                continue
            directions = nonzero_directions(quotient_basis)
            for direction in directions:
                counters["direction_tests"] += 1
                a3 = find_product_in_coset(s2, direction)
                if not a3:
                    continue
                s3 = canonical(insert(as_basis(s2), a3["actual_product"]))
                remaining = nonzero_directions(target_quotient_basis(targets, s3))
                if len(remaining) != 1:
                    continue
                a4 = find_product_in_coset(s3, remaining[0])
                if a4:
                    counters["completion_successes"] += 1
                    return {"status": "exact", "features": list(names),
                            "and_count": 4,
                            "and_nodes": [witness1, witness2, a3, a4],
                            "counters": counters,
                            "elapsed_seconds": time.time() - started}
            if counters["second_extensions"] % 1000 == 0:
                print("progress", counters, flush=True)
            if max_second is not None and counters["second_extensions"] >= max_second:
                return {"status": "smoke_limit", "features": list(names),
                        "counters": counters, "elapsed_seconds": time.time() - started}
            if time.time() - started > timeout_seconds:
                break
    return {"status": "timeout_or_no_witness", "features": list(names),
            "counters": counters, "elapsed_seconds": time.time() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", nargs=2, default=["R1", "R2"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-first", type=int, default=10000)
    parser.add_argument("--max-second", type=int)
    args = parser.parse_args()
    result = search_pair(args.features, args.timeout, args.max_first, args.max_second)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
