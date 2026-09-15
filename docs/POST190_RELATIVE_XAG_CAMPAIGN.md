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
| X quotient prefix | 44 | code0, raw | UNSAT | UNSAT | timeout at 45 s |
| Y comparison-B prefix | 61 | code0, raw | UNSAT | UNSAT | timeout at 45 s |

The internal timing maxima are 43 and 60 respectively because the saved timing
vectors use zero-based arrival slots.  No full residual or physical encoder was
found in this initial run, and `artifacts/190/` was not modified.

The cheap portfolio screen also tested X quotient indices 0–2 (depths 43, 44,
41), Y quotient indices 0–2 (depths 38, 38, 39), and comparison-B indices 0–2
(depths 60, 63, 64).  Every one returned exact finite-bound UNSAT for r=0 and
r=1.  The r=2 search spends nearly all of its time generating the next affine
library after the 42k–43k distinct one-product spans; both primary r=2 probes
therefore timed out before exhausting that finite state space.  This is an
enumeration-performance limit, not an UNSAT result.  No diverse complete XAG,
physical reconstruction, or non-NIST product was promoted.

Reproduction:

```sh
PYTHONPATH=src .venv/bin/python - <<'PY'
from post190_relative_xag import load_prefix, residual_search
for path, side in [
    ('artifacts/post190_information_space/quotient_x/frontier.json', 'x'),
    ('artifacts/post190_information_space/comparison_cached/B/frontier.json', 'y')]:
    p = load_prefix(path, 0, side)
    print(side, residual_search(p, max_products=1, max_stages=1, seconds=30))
PY
.venv/bin/python -m pytest -q tests/test_post190_relative_xag.py
```
