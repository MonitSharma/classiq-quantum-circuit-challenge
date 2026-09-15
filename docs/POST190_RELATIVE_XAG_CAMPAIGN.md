# Prefix-relative XAG campaign

This campaign adds an exact 64-bit residual synthesizer in
`src/post190_relative_xag.py` and the public bounded entry point
`src/post190_relative_xag_sat.py`.  It starts from the actual clean affine
span of a saved nine-wire frontier state, enumerates every affine form, and
adds products from that current span rather than restricting products to the
original NIST witness bank.  States are canonicalized by affine span; each
retained product keeps multiple operand-mask decompositions for later physical
scheduling.

The solver is exact for a completed finite bound.  It distinguishes `SAT`,
`UNSAT` (finite space exhausted), and `timeout` (the deadline interrupted
enumeration).  It uses all 64 legal coordinate inputs; no sampled constraints
are used.  The physical prefix metadata is loaded and preserved, but no
candidate is promoted to an encoder until joint-stage reconstruction and
quantum verification are added.

Initial exact results from the saved index-0 X and Y two-goal prefixes:

| Prefix | Documented depth | Present goals | r=0 | r=1 | r=2 |
|---|---:|---|---|---|---|
| X quotient prefix | 44 | code0, raw | UNSAT | UNSAT | **UNSAT** |
| Y comparison-B prefix | 61 | code0, raw | UNSAT | UNSAT | **UNSAT** |

The internal timing maxima are 43 and 60 respectively because the saved timing
vectors use zero-based arrival slots.  No full residual or physical encoder was
found in this initial run, and `artifacts/190/` was not modified.

The specialized r=2 certificates are in
`artifacts/post190_relative_xag_r2/x44.json` and `y61.json`. Both have
quotient rank 2, exactly 1,024 base affine forms, 524,800 unordered pairs,
and zero realizable first products in `{q1, q2, q1+q2}`. Since every r=2
solution must have its first product in one of those three classes, this is an
exhaustive finite UNSAT result; no second-product pairs are needed. The
quotient-space reduction collapses the old 42k–43k first-product semantic
states to zero useful branches for both primary prefixes.

The exact r=2 portfolio certificate is
`artifacts/post190_relative_xag_r2/portfolio.json`. It also tested X quotient
indices 0–2 (depths 43, 44,
41), Y quotient indices 0–2 (depths 38, 38, 39), and comparison-B indices 0–2
(depths 60, 63, 64).  Every one returned exact finite-bound UNSAT for r=0 and
r=1 and r=2. Every r=2 portfolio branch also had quotient rank 2, 1,024
base forms, 524,800 first pairs, and zero useful first classes. No physical
reconstruction was warranted.

Reproduction:

```sh
PYTHONPATH=src .venv/bin/python -m post190_relative_xag_sat --frontier artifacts/post190_information_space/quotient_x/frontier.json --side x --index 0 --seconds 120 --out artifacts/post190_relative_xag_r2/x44.json
PYTHONPATH=src .venv/bin/python -m post190_relative_xag_sat --frontier artifacts/post190_information_space/comparison_cached/B/frontier.json --side y --index 0 --seconds 120 --out artifacts/post190_relative_xag_r2/y61.json
.venv/bin/python -m pytest -q tests/test_post190_relative_xag.py
```
