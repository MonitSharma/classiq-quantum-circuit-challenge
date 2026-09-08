# Side-separated minimum-MC rank report

## Conclusion

The side-separated rank hypothesis was tested through its single-pair gate. The
x and y computations do schedule concurrently, but the available repository
XAG backend cannot produce valid one-output-plus-two-scratch schedules for most
factor functions. The full rank oracle was therefore not attempted.

## Backend and inventory

`src/rank_factor_inventory.py` verified all three ten-term bases against the
exact target and recorded 30 deduplicated six-variable functions in
`artifacts/rank_factor_inventory.json`. The supplied Pareto factorization was
restored only after this exact check.

The backend used for the reversible probe was the existing formula-derived
XAG graph (`src/xag.py`) with bounded pebbling. A genuine external
`xag_minmc_resynthesis` or exact SAT minimum-MC backend was not available in
the installed environment, so no minimum-MC claim is made.

## Reversible and parallel results

`src/parallel_rank_pair.py` showed that the existing formula representation
usually cannot fit one output plus two scratch wires per side.

`src/parallel_rank_pair_xag.py` used separate x wires q0..q5 and y wires
q6..q11, with x output/scratch q12..q14 and y output/scratch q15..q17.
The one surviving Pareto pair measured:

- x computation: 47 depth / 29 CX;
- y computation: 45 depth / 27 CX;
- parallel compute: 47 depth / 58 CX;
- complete compute/phase/uncompute pair: **50 depth / 65 CX**;
- width: 18.

An independent sparse basis simulation checked all 4096 x/y basis inputs for
that pair: inputs were preserved, the pair phase was correct, ancillas were
restored, and the common phase was 1.

The strict XAG probe produced usable pairs for only 2/10 `pair_terms`, 1/10
`rank_terms`, and 2/10 `rank_mc_pareto_terms`. Since the ten-term oracle cannot
be assembled from this backend, no complete rank-oracle depth/CX/width exists
for this experiment.

## Comparison and bottleneck

| reference | depth | CX | width |
|---|---:|---:|---:|
| existing pair oracle | 779 | 736 | 18 |
| protected global best | **531** | **1020** | **18** |
| live target snapshot | ~291 | — | — |
| side-separated surviving pair | 50 | 65 | 18 |

The 50-depth pair is not a complete oracle and must not be compared as a
submission score. The dominant bottleneck is reversible pebbling of the
difficult six-variable factors with only two scratch wires per side, not
x/y-side parallelism.

## Verification and next experiment

No complete QASM candidate was accepted. The protected 531 QASM remains the
only official local best and is exhaustively verified on all 4096 basis inputs.
The surviving pair was locally exhaustively checked; it was not a complete
challenge oracle.

The genuinely different next step is to integrate a real six-variable
minimum-MC/XAG database or bounded exact SAT synthesis, then rerun the same
side-separated compiler. Repeating the current formula/XAG backend, basis
search, or generic global cleanup is not justified by these measurements.

