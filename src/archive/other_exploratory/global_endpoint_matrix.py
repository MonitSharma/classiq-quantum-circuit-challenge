"""Analyze and factor the GF(2) interaction matrix of global phase endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from search import logo


def xor_rows(a, b):
    return [x ^ y for x, y in zip(a, b)]


def factor_gf2(matrix):
    rows = [list(row) for row in matrix]
    m = len(rows); n = len(rows[0]) if m else 0
    work = [sum(bit << j for j, bit in enumerate(row)) for row in rows]
    pivot_rows = []
    pivot_cols = []
    r = 0
    for c in range(n):
        pivot = next((i for i in range(r, m) if (work[i] >> c) & 1), None)
        if pivot is None:
            continue
        work[r], work[pivot] = work[pivot], work[r]
        for i in range(m):
            if i != r and ((work[i] >> c) & 1):
                work[i] ^= work[r]
        pivot_rows.append(r); pivot_cols.append(c); r += 1
        if r == m: break
    rank = r
    # Select an independent set of original rows; the matrix is tiny, so a
    # greedy rank test is clearer and safer than exposing elimination internals.
    pivot_original = []
    for i in range(m):
        trial = pivot_original + [i]
        if independent_rows(matrix, trial) > len(pivot_original):
            pivot_original.append(i)
        if len(pivot_original) == rank: break
    v_rows = [matrix[i] for i in pivot_original]
    # Solve each row against the selected basis. The rank is at most eleven,
    # so exhaustive coefficient search is trivial and completely unambiguous.
    u = []
    for original in matrix:
        target = sum(bit << j for j, bit in enumerate(original))
        found = None
        for coeff in range(1 << rank):
            value = 0
            for k in range(rank):
                if (coeff >> k) & 1:
                    value ^= sum(bit << j for j, bit in enumerate(v_rows[k]))
            if value == target:
                found = coeff; break
        assert found is not None
        u.append([(found >> k) & 1 for k in range(rank)])
    return rank, pivot_original, u, v_rows


def independent_rows(matrix, indices):
    vals = [sum(bit << j for j, bit in enumerate(matrix[i])) for i in indices]
    rank = 0
    for c in range(len(matrix[0]) if matrix else 0):
        p = next((i for i in range(rank, len(vals)) if (vals[i] >> c) & 1), None)
        if p is None: continue
        vals[rank], vals[p] = vals[p], vals[rank]
        for i in range(len(vals)):
            if i != rank and ((vals[i] >> c) & 1): vals[i] ^= vals[rank]
        rank += 1
    return rank


def main():
    source = json.loads(Path("artifacts/global_12_edge_endpoints.json").read_text())
    xs = sorted({r["x_truth_table"] for r in source["edges"]})
    ys = sorted({r["y_truth_table"] for r in source["edges"]})
    xi = {v: i for i, v in enumerate(xs)}; yi = {v: i for i, v in enumerate(ys)}
    matrix = [[0 for _ in ys] for _ in xs]
    for edge in source["edges"]:
        matrix[xi[edge["x_truth_table"]]][yi[edge["y_truth_table"]]] ^= 1
    rank, pivots, u, vrows = factor_gf2(matrix)
    terms = []
    for k in range(rank):
        xt = 0
        for i, flag in enumerate([row[k] for row in u]):
            if flag: xt ^= xs[i]
        yt = 0
        for j, flag in enumerate(vrows[k]):
            if flag: yt ^= ys[j]
        terms.append({"index": k, "x_truth_table": xt, "y_truth_table": yt})
    mismatches = []
    for x in range(64):
        for y in range(64):
            value = 0
            for term in terms: value ^= ((term["x_truth_table"] >> x) & 1) & ((term["y_truth_table"] >> y) & 1)
            if value != int(logo(x, y)): mismatches.append([x, y])
    Path("artifacts/global_endpoint_matrix.json").write_text(json.dumps({
        "x_truth_tables": xs, "y_truth_tables": ys, "matrix": matrix, "rank": rank,
        "pivot_x_indices": pivots, "factorization_mismatches": mismatches,
    }, indent=2))
    Path("artifacts/global_endpoint_rank_terms.json").write_text(json.dumps({
        "terms": terms, "rank": rank, "inputs_checked": 4096, "mismatches": len(mismatches)
    }, indent=2))
    print(json.dumps({"unique_x": len(xs), "unique_y": len(ys), "rank": rank,
                      "factorization_mismatches": len(mismatches), "terms": terms}, indent=2))


if __name__ == "__main__": main()
