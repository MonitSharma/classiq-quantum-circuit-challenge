# Multiplicative-depth campaign

## Objective

This campaign is separate from the protected 524-depth oracle work. It asks
whether the exact logo has a shallow XOR--AND graph (XAG) when sequential
nonlinear layers are optimized before reversible or quantum lowering.

An affine XOR combination is free for this structural metric. For an AND node
`g = a AND b`,

```text
MD(g) = 1 + max(MD(a), MD(b)).
```

AND count and multiplicative depth are therefore different objectives. A
large, shallow graph may be more useful than a compact but deeply sequential
one.

## Exact target

The authoritative predicate is `src/search.py::logo`, with little-endian
`x = q[0:6]` and `y = q[6:12]`. The independent evaluator in
`src/md_xag.py` uses 4096 truth-table points and constant-one signal 0.

| Property | Value |
|---|---:|
| Variables | 12 |
| Truth-table points | 4096 |
| Marked points | 1097 |
| Algebraic degree | 12 |
| Nonconstant ANF terms | 886 |
| Truth-table SHA-256 (little-endian bytes) | `d86d44aa45393ecc14ddfed0ed08d97e550a2786d58f61173fa71a6394253cf1` |

The deterministic truth table is exported at
`artifacts/multiplicative_depth/logo_truth.hex`. The independent evaluator and
its tests do not trust a compiler's correctness report.

## Existing exact XAG audit

The audit is saved at
`artifacts/multiplicative_depth/existing_xag_audit.json`.

| Network | Exact | ANDs | MD | ANDs per MD layer | Live-width estimate |
|---|---:|---:|---:|---:|---:|
| Balanced ANF monomials | yes | 5096 | 4 | 2767, 1390, 812, 127 | 5096 |
| Shared rank-factor formula XAG | yes | 97 | 6 | 29, 21, 20, 14, 10, 3 | 97 |

The balanced ANF network is an explicit MD=4 upper bound, but its enormous
layer and live widths make it unsuitable for six-ancilla quantum realization.
The shared rank-factor formula graph is much smaller and reaches MD=6. Its
layer width is promising, but the naive topological schedule keeps all 97
nonlinear values live; this is a structural result, not yet a quantum
candidate.

The shared XAG was independently reconstructed from the repository's formula
graph and verified by `md_xag.XAG.evaluate()` over all 4096 points. The
existing shared-XAG phase pilot is separately recorded in
`docs/PHASE_HISTORY.md`; its reversible pebbling cost must not be confused
with the graph's multiplicative depth.

## Current conclusion

**Conditional GO for structural optimization.** The exact logo demonstrably
has shallow nonlinear structure (MD 6 with 97 ANDs, and a trivial MD 4
construction with large width). The next required work is depth-oriented XAG
rewriting, controlled size growth, affine-basis search, and live-width-aware
analysis. No QASM lowering should begin until a schedule with materially
smaller nonlinear live width is found.

## Reproducibility

```bash
PYTHONPATH=src .venv/bin/python src/md_xag.py \
  --out artifacts/multiplicative_depth/anf_balanced_baseline.json \
  --truth-hex artifacts/multiplicative_depth/logo_truth.hex
PYTHONPATH=src .venv/bin/python src/audit_multiplicative_depth.py
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```
