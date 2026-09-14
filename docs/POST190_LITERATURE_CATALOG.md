# Literature-guided synthesis and concrete NIST witnesses

September 15, 2026. **Protected full oracle remains 190 depth / 857 CX / 18 wires.**
This research produced six verified Boolean component witnesses, not an improved
submission. Sub-140, sub-100 and rank one remain unfinished.

## Published methods actually tested

[Soeken, Determining the Multiplicative Complexity of Boolean Functions using SAT](https://arxiv.org/html/2005.01778v1)
gives normal-form reductions for exact XAG search. Implemented internal-constant
normalization, strict commutative operand ordering, nonsubset fanin supports and
node-use constraints in `src/post190_literature_xag.py`. Added our independent
high-degree output-rank clauses and optional AND-depth constraints. Exhaustive
four-bit ordering tests and positive/negative Boolean controls pass (two tests).
This improves the formulation; it does not certify a native-depth optimum.

Four externally bounded runs each exhausted 45 seconds:

| Side | AND nodes | AND-depth bound | Result |
| --- | ---: | ---: | --- |
| y | 6 | unrestricted | timeout |
| x | 6 | unrestricted | timeout |
| y | 7 | 3 | timeout |
| x | 7 | 3 | timeout |

Reports are `artifacts/post190_lit_{x,y}{6,7d3}_wall.json`. No SAT or UNSAT
conclusion was obtained. These short probes are not evidence of impossibility.
All four guard-managed processes finished; externally owned jobs were untouched.

[Xor-And-Inverter Graphs for Quantum Compilation](https://www.nature.com/articles/s41534-021-00514-y)
is relevant to extracting nonlinear structure, but its reported T-resource
savings include measurement-based uncomputation. Those numbers cannot be
substituted for this challenge's standalone unitary `u3`/`cx` depth. Our
measurements use actual inverse circuits and restored work wires.

## Constructive catalogue result

[Calik, Turan and Peralta, The Multiplicative Complexity of 6-variable Boolean Functions](https://eprint.iacr.org/2018/002.pdf)
provides optimum circuits for six-variable equivalence-class representatives.
Its single-output result does not bound the shared cost of three outputs or
reversible workspace. We retrieved the public
[NIST data repository](https://github.com/usnistgov/Circuits/tree/master/data/slp/n6)
and matched our predicates to its circuits, rather than inferring equivalence
from spectra alone.

Pipeline in `src/post190_nist_catalog.py`:

1. Screen representatives by sorted absolute Walsh spectra.
2. Backtrack invertible frequency-basis maps and translations, retaining
   consistent affine sign patterns.
3. Recover the input affine permutation and output affine correction.
4. Parse the explicit SLP, substitute our coordinates and check every input.
5. Merge circuits using exact truth-table linear-span elimination; measure
   individual witnesses with the existing three-ancilla register compiler.

All six code bits have **verified five-AND witnesses**. Spectrum candidate
counts are y0:3, y1:290, y2:1, x0:33, x1:5, x2:217. All affine maps are bijective,
and each final witness matches the actual protected target on all 64 inputs.
The compact circuit format alone was initially misread as final-node plus
linear output; the explicit SLP includes additional node XORs. The failed
interpretation was rejected before measurement. Saved witnesses use the
explicit SLP and pass the independent check.

The selected independent witnesses merge to **15 ANDs for x and 14 for y**.
That is a construction, not a shared-AND lower bound. Different equivalent
representatives or transformations could have different sharing.

## Measured register cost

Each individual witness was asked to produce its bit and two zero outputs,
keeping all six input wires intact, using the restricted register-span scheduler.

| Predicate | Scheduler result | Node toggles | Native encoder depth | CX |
| --- | --- | ---: | ---: | ---: |
| y0 | found | 11 | 127 | 121 |
| x0 | found | 11 | 124 | 120 |
| y1 | restricted model exhausted | — | — | — |
| y2 | restricted model exhausted | — | — | — |
| x1 | restricted model exhausted | — | — | — |
| x2 | restricted model exhausted | — | — | — |

Both found circuits pass quantum compute/phase/inverse verification on all 64
inputs, with maximum errors 2.66e-15 and 2.26e-15. These are single predicates,
not three-output encoders, and do not improve the protected 77-layer loaders.
Exhaustion applies only to the named-signal, input-preserving register model;
it does not exclude input-overwriting or another circuit for the predicate.
No full-oracle improvement is claimed, so these are not submission QASMs.

## Reproduction and artifacts

Everything is under `artifacts/post190_nist_catalog/`: source checksums, affine
maps, selected source SLPs, six witnesses, two merged witnesses, native component
QASMs and measurements. Cached public data has approximately 62 MB; it is not
challenge data or authentication material.

From the workspace root, run successive stages:

```sh
.venv/bin/python src/post190_nist_catalog.py screen
.venv/bin/python src/post190_nist_catalog.py map
.venv/bin/python src/post190_nist_catalog.py extract
.venv/bin/python src/post190_nist_catalog.py merge
.venv/bin/python src/post190_nist_catalog.py measure
.venv/bin/python -m pytest tests/test_post190_nist_catalog.py -q
```

The script uses cached source data, performs no network requests and never
writes the protected package. The new artifact regression test passes.
Protected QASM SHA rechecked unchanged:
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`.

## What this changes

There is now a constructive source of exact nonlinear predicate circuits;
waiting for a shared six-AND SAT result is not the only route to witnesses.
However, separately minimizing each output produces expensive cleanup and
little sharing for these choices. The next useful search should optimize the
three outputs and their register schedule jointly, or allow different class
labels and measure the resulting phase kernel. A universal depth ceiling has
not been proved. This round does not establish a route to sub-140.
