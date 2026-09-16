# September 16: assessment and implementation of the user's Direct-E proposal

The protected complete oracle remains **185 depth / 854 CX / 18 qubits**.
This pilot has not produced an exact Direct-E classifier, a sub-185 oracle,
or a leaderboard submission. The 135/137 numbers below are conditional
architecture budgets, not measured depths of valid logo oracles.

## Assessment against existing work

Read the attached analysis, `HANDOFF.md`, `EXPERIMENTS.md`, `CURRENT_DESIGN.md`,
`COMPLETE_METHOD_POSTMORTEM.md`, `POST190_NEW_ARCHITECTURES.md`, and the relevant
source implementations before selecting experiments.

| Proposal | Evidence and correction |
| --- | --- |
| Seven-layer Margolus | Correct: explicit Ry/CX construction is 7 native layers, 3 CX, 4 U3. Full 8x8 operator check confirms CCX permutation up to relative phases. However, **the existing native Qiskit RCCX already takes 7 layers**. The old direct template's 9 was a loose assertion/budget, not its actual compiled cost. `PHASE_HISTORY.md` and `destructive_semantic_search.py` already record 7. |
| Midpoint phase on an affine combination of wires | Correct construction: E, parallel Z mask, literal E inverse. Already explored in `destructive_semantic_search.affine_span_solution`, `destructive_dirty_search.phase_support`, and phase-history searches. The old direct SAT template specifically still fixes q17, so lifting that restriction there is useful. |
| Free first nonlinear stage and paid affine prefix | The old direct SAT model fixes six adjacent input pairs. V2 removes this restriction and permits destructive targets on all 18 wires. |
| Global affine ANF 886 to 264 in ten operations | **Independently reproduced**, with an exact saved coordinate mapping and inverse replay over 4,096 inputs. ANF count remains a proxy, not a depth estimate. |
| Gaussian elimination as a distance score | Elimination decides exact membership, but the Hamming weight of its remainder is not nearest-span distance. V2 uses an exact Walsh-histogram calculation instead. |
| Quasar | Real public PLDI 2026 artifact, absent from the previous experiment inventory. Successfully installed in an isolated temporary dependency directory and tested. Default extraction favors CX count; whole-oracle depth did not improve in this pilot. |

The user analysis's architecture direction is worth testing. Its primitive-cost
change is not a new optimization, and several components have precedents here.
The new work combines these components under explicit physical depth budgets
and independently checks the claimed affine witness.

## Reproduced affine witness

`src/direct_e_affine_seed.py` greedily checks 132 CNOT and 12 X elementary
coordinate changes at each of ten steps. Counts are:

`886 -> 646 -> 480 -> 442 -> 412 -> 372 -> 345 -> 282 -> 270 -> 274 -> 264`.

Chronological physical encoder operations:

```text
X(2)
CX(2,3)
CX(11,9)
CX(5,0)
CX(3,1)
CX(11,10)
CX(5,11)
CX(11,4)
CX(5,2)
CX(3,2)
```

Saved witness: `artifacts/direct_e_v2_affine_reproduced.json`. If the listed
involutions are T1 through T10, transformed function g(z) is
f(T1(T2(...T10(z)))); applying those gates chronologically encodes x into
z=T10(...T2(T1(x))). Both orientations are checked explicitly. One X and nine
CX layers are charged inside the seeded forward budget; no affine gates are
free. The seed is allowed to mutate subsequently.

## Direct-E v2 implementation

`src/direct_e_v2.py` provides:

- Physical disjoint X/CX/CCX layers, with free first-layer topology and dirty
  data targets. Optional gates allow sparse layers.
- Full 4,096-bit truth tables for every wire.
- Exact nearest affine output parity: accumulate the signed target histogram
  indexed by the 18-bit midpoint word, then take its Walsh transform. For
  maximum absolute correlation c, the nearest parity has (4096-c)/2 errors.
  This is checked against the older exhaustive enumeration of all 2^18 masks.
- Whole-layer and interior gate mutations with simulated annealing, exact
  truth-table scoring, saved best networks, and paid structured initialization.
- SAT synthesis of arbitrary selected matching layers and a free output mask,
  including constant phase; fixed layers replay literally. All sampled SAT
  results are checked on all 4,096 inputs before they can become candidates.
- Literal seven-layer Margolus gates followed by parallel Z and the actual
  inverse. An output constant changes only the allowed shared global phase.
- QASM emission only for an exact logo truth table, followed by the repository
  exhaustive verifier. No approximate checkpoint is exported as a candidate.

The conservative full depth ceiling is `2*(7*nonlinear + affine)+1`.
Boolean complements take native layers too. These are schedule upper bounds
conditional on finding the exact predicate within the template.

## Bounded search results

Each run below used approximately 60 seconds of annealing after initialization.
46,109 proposals were evaluated across eight runs. Distances are exact minimum
errors across **all** midpoint parities and all 4,096 logo inputs.

| Nonlinear / affine layers | Conditional full depth | Initialization | Proposals | Best errors |
| --- | ---: | --- | ---: | ---: |
| 6 / 26 | 137 | Empty network | 5,774 | 1,091 |
| 7 / 19 | 137 | Empty network | 5,774 | 827 |
| 8 / 12 | 137 | Empty network | 5,777 | 815 |
| 7 / 18 | 135 | Empty network | 5,761 | 809 |
| 6 / 26 | 137 | Paid affine + greedy nonlinear seed | 5,731 | 685 |
| 7 / 18 | 135 | Paid affine + greedy nonlinear seed | 5,798 | **657** |
| 8 / 12 | 137 | Paid affine + greedy nonlinear seed | 5,735 | 685 |
| 7 / 18 | 135 | Greedy seed without affine prefix, matched seed | 5,759 | 827 |

Best checkpoint: `artifacts/direct_e_v2_seeded_n7_a18_s26185/best.json`.
Its 657 errors make it invalid as an oracle. A control run with the same greedy
initializer, seed26185, nonlinear/affine budgets and60-second search limit,
but no affine prefix, ends at827 errors. Before annealing the respective
distances are685 with the prefix and1097 without it: greedy product selection
gets stuck at the constant classifier in the original coordinates. This one
matched control supports using the prefix; it is not a multi-seed statistical
result or evidence of exact completion. The initial networks are saved in
`artifacts/direct_e_v2_initialization_comparison.json`.
Earlier semantic searches used different, often larger, depth budgets; their
residuals are not directly comparable with these numbers.

Two restricted repairs of that checkpoint timed out: free layers 23/24 with
63 samples and a 10-second solver limit, then layers 22/23 with 63 samples and
15 seconds. The latter frees the final nonlinear layer and its predecessor.
No UNSAT or impossibility conclusion follows. Records are in
`artifacts/direct_e_v2_repair_seeded/` and `artifacts/direct_e_v2_repair_prefix/`.
Fully free 6/26, 7/18 and 8/12 template probes each timed out on 32 samples
with a ten-second requested solver limit (observed solver times approximately
12.94, 11.94 and 10.13 seconds). They are recorded separately under
`artifacts/direct_e_v2_free_template/`; no infeasibility conclusion follows.

## Quasar integration and precision audit

Primary references:

- [PLDI 2026 paper page](https://pldi26.sigplan.org/details/pldi-2026-papers/11/Equality-Saturation-for-Quantum-Circuit-Optimization).
- [Official artifact v3](https://zenodo.org/records/19571754), archive MD5
  `ff3a49973c97316bca0fb2d347ea5478` verified after download.
- [Margolus gate optimality, Song and Klappenecker](https://arxiv.org/abs/quant-ph/0312225).

The reported 24.2% geometric-mean benchmark depth reduction is not a prediction
for this oracle. The Seq-EG implementation actually uses CX/RZ/SX/X/Z gates;
although an `ibm` name lists U3 in a table, the parser does not implement a U3
DSL operation. `src/post185_quasar_probe.py` explicitly rebases with
`qubits_initially_zero=False` and checks physical output layout before use.

The official small benchmark ran successfully (16 to 12 CX at exploration
step 3, two iterations). On our full circuit, exploration steps 3 and 4 remove
one CX, but the output rebases to **187 / 853**. A step-7 attempt was externally
terminated at 70 seconds without a completed optimizer result. These are
bounded runs, not a complete evaluation of Quasar.

The upstream parser uses `Fraction(float).limit_denominator()` with default
denominator cap 10^6. This perturbs decimal rotation angles: the first
verified output had maximum error about 5.75e-11. Although under the existing
1e-10 verifier threshold, that precision loss is avoidable. The integration
now saves a separate two-line derivative of `optimize.py` removing that
rational approximation and changing output formatting from 15 to 17 digits.
The downloaded artifact is unchanged. Source/patch hashes are recorded.

With that correction the 187/853 output has error about 2.39e-14. Exact
rescheduling reaches **186 / 853**, verified on all inputs with error about
2.25e-14. CP-SAT proves 186 optimal for this fixed gate/commutation model;
this is not a lower bound on all equivalent circuits. Thus the new CX saving
does not beat the protected depth of 185.

Records: `artifacts/post185_quasar_precise/`,
`artifacts/post185_quasar_precise_scheduled/`, plus historical unpatched probes
`artifacts/post185_quasar_v1/` and `artifacts/post185_quasar_v2/`.

## Validation and reproduction

15 focused and regression tests pass:

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/test_direct_e_v2.py tests/test_post190_new_architectures.py \
  tests/test_native_wire_identity.py
```

Coverage includes full Margolus matrix, native RCCX calibration, exact nearest
parity against exhaustive enumeration, high-weight phase masks, dirty-target
phase cancellation after QASM serialization, disjoint-layer mutations,
non-adjacent first-layer SAT positive control, affine witness replay, and
negative controls. A preliminary X-layer test using only inputs 0..31 exposed
the expected underdetermination of unsampled high bits; its full-input check
correctly rejected the sampled solution. The positive test now constrains all
inputs. This was not a valid-oracle result or a change to correctness criteria.

Fresh runs (output paths must not exist):

```bash
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python src/direct_e_affine_seed.py \
  --out artifacts/NEW_affine.json
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python src/direct_e_v2.py \
  --outdir artifacts/NEW_direct --nonlin 7 --affine 18 --seconds 60 \
  --preconditioner artifacts/NEW_affine.json --seed 26185
```

Quasar requires its public artifact plus isolated `egglog==13.0.0` and
`pulp==3.3.0` dependencies. The pilot used `/tmp/classiq-quasar-20260916/` and
`/tmp/classiq-quasar-deps-20260916`; these temporary paths may need recreating.
Wrap `src/post185_quasar_probe.py` in `src/run_bounded.py`: the optimizer's own
time limit is only checked between e-graph iterations. Use `--score-only` on
the output directory to rebase unique snapshots and exhaustively verify them.

## What the next search should change

Do not repeat the unseeded pilot or infer near-completion from 657 errors.
The matched initialization control supports retaining the reproduced affine
prefix. The next useful change is larger semantic block replacement or
alternative structured affine seeds, evaluated under the same physical depth
budget. Longer unrestricted SAT timeouts alone have not
provided evidence of a viable route. Quasar's deeper rewrite exploration and
alternate extraction objectives remain untested; its first successful output
already shows why CX count cannot stand in for depth.
