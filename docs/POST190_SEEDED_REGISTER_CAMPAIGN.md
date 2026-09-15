# Seeded semantic register compiler and improved affine witnesses

Protected full result: **190 depth / 857 CX / 18 qubits**, unchanged SHA
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`.
The requested complete nine-wire encoder below77 has **not** been found.
No rank-one or sub137 result is claimed.

## Exact Boolean improvements

`src/post190_nist_variants.py` enumerates multiple affine realizations of the
same NIST representatives instead of stopping at the first equivalence map.
Every instantiated witness is checked on all64 inputs. Merging uses exact
GF(2) truth-function relations, not floating-point rank.

| Side | Previous merged AND count | New count | Logical level widths |
| --- | ---: | ---: | --- |
| x | 15 | **14** | **[8,3,3]** |
| y | 14 | **13** | **[6,4,3]** |

Representative choices are unchanged. The x14 result was independently
recreated without the unavailable review attachment. The y13 is a further
local result from widening affine enumeration.

Best examples:
- `artifacts/post190_nist_variants/x_candidate_0.json`
- `artifacts/post190_nist_variants_wide/y_candidate_0.json`

The wider run retained four x14 and eight y13 candidates. It checked all32
triples in its generated x bank and2882 distinct sampled y triples. The
bounded mapping enumeration is NOT exhaustive over all affine realizations.
The counts do not imply any reversible/native-depth bound.

## Actual mutable-wire scheduler

`src/post190_semantic_register.py` represents all nine wires as exact64-bit truth
tables. It finds affine expressions for seed AND operands in the currently held
functions, exposes controls by reversible CX/X operations, and applies RCCX to
any other target, including a coordinate containing nonzero data. That target
becomes its OLD function XOR the product. Control frames remain in place.

The optional `--mix` move first copies a target's value into another spectator
register by CX before the nonlinear update. This explores more ways of keeping
useful input information when overwriting a coordinate. All updates are exact.

Goals are the three protected code functions plus the raw tag; they may finish
on any four distinct wires. A final linear frame materializes them where cheap.
Native timing accounts for individual RCCX decomposition gates, allowing their
supports to overlap across logical operations. Any completed candidate is
compiled and checked quantum-mechanically on every input, with actual inverse
cleanup. CLI output QASM is parsed back and checked before reporting it.

Search limitations are explicit: this is a bounded beam search using AND
products from the supplied witness, two selected control-frame choices, and
limited target-mixing moves. Affine-span deduplication and heuristic rankings
can discard useful physical layouts. The closure check relaxes storage and was
not strong enough to reject states in these runs. None of the failures is an
UNSAT result or a proof against more general input-overwriting circuits.

## Search outcomes

- Initial x15/y14 runs exposed a frame-cycling scoring problem; they found no
  complete encoder. Deduplication and remaining-nonlinear-level scoring were
  added before subsequent runs.
- x14/y14 runs and a12-candidate portfolio found no complete encoder.
- Further x14/y14 runs with spectator mixing found no complete encoder.
- Two y13 runs with mixing, beam48 and20-second budgets examined277830 and
  266560 updates before timeout. Their best recorded frontiers had two of four
  required functions in the affine span, not all four. These are partial
  search states, not encoder artifacts or verified depth gains.

Reports/logs are in `artifacts/post190_semantic_*` and
`artifacts/post190_semantic_portfolio/`. All new jobs finished. No blind SAT
sample campaign or global62-node rewrite was launched.

## Free-output composition and verification

`src/post190_free_output_compose.py` handles the protected kernel's physical bit
permutation explicitly before mapping it onto arbitrary descriptor wires.
It composes the actual encoder inverse; coordinate wires cannot be silently
permuted on exit.

The control using existing encoders is **196/866/18**, all4096 inputs pass at
7.99e-15 with zero ancilla error. This is a correctness control, not an
improvement. Its SHA is
`61f52003c2a58df490b7edd6f08031a6fd6979a073a0b8d9321d2330ffbb8066`.
Artifacts: `artifacts/post190_free_output_control/`. The explicit permutation
restoration costs gates; this control illustrates why simply adding an assumed
35-layer kernel to future encoder estimates is insufficient.

Six focused regression tests pass, covering actual dirty-target semantics,
coordinate output placement, complete synthetic synthesis and quantum inverse,
affine-span normalization, and exhaustive x14/y13 Boolean correctness.
The synthetic depth7 positive control is NOT a logo encoder.

## Reproduce

From the workspace root, using fresh output directories:

```sh
.venv/bin/python src/post190_nist_variants.py --outdir /tmp/nist_variants_new --count 256 --trials 5000
.venv/bin/python src/post190_semantic_register.py --witness /tmp/nist_variants_new/y_candidate_0.json --side y --outdir /tmp/y13_schedule_new --seconds 20 --beam 48 --mix
.venv/bin/python -m pytest tests/test_post190_semantic_register.py -q
```

If a complete schedule is produced, compose its saved folder with:

```sh
.venv/bin/python src/post190_free_output_compose.py --y /tmp/y13_schedule_new --outdir /tmp/y13_oracle_new
```

The composition command runs full exact-file exhaustive numerical verification.
Do not run it on an incomplete schedule folder without an encoder artifact.

## Remaining bottleneck

The improved Boolean witnesses are real, but no complete physical allocation
has passed the below77 milestone. Current searches reach one code bit plus the
raw tag and then fail to retain enough useful functions to finish all outputs.
The next compiler experiment should broaden the permitted register-frame moves
or seed a local reversible repair from these partial trajectories; another
small AND-count reduction alone is not evidence that allocation is solved.
