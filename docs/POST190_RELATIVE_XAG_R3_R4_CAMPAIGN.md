# Prefix-relative r=3 certificate

The quotient-aware r=3 certificate is implemented in
`src/post190_relative_xag_r3.py`. It enumerates all 1,024 affine forms of the
saved prefix span and all 524,800 unordered base pairs. Product truth tables
are reduced modulo the prefix span and then modulo the two-goal quotient plane.
For each distinct first-product quotient representative it exhaustively tests
the p-dependent second-product criterion using the precomputed spaces
`L_w = S + wS`.

Primary results:

| Prefix | Nonzero product classes | G buckets | Histogram | p,w,g tests | Result |
|---|---:|---:|---|---:|---|
| X44 | 42,077 | 42,077 | 42,077×1 | 129,260,544 | UNSAT |
| Y61 | 43,053 | 43,053 | 43,053×1 | 132,258,816 | UNSAT |

Both certificates have quotient rank 2, zero base-only G-coset collisions,
and zero p-dependent membership hits. Thus every legal first two-product
prefix still has quotient deficit 2; with one product remaining, r=3 is
exactly UNSAT in this Boolean model. These are finite exhaustive certificates,
not timeout-based conclusions.

The shallow portfolio (X quotient indices 0–2, Y quotient indices 0–2, and
comparison-B indices 0–2) likewise returned exact r=3 UNSAT with singleton
buckets and zero membership hits. Full JSON reports are in
`artifacts/post190_relative_xag_r3/`.

The saved prefix metadata and protected `artifacts/190/` package are unchanged.
No r=4 search has been promoted yet; the next experiment is the requested
depth-2 stage-pattern search (1+3, 2+2, 3+1), with no generic r=4 expansion.
