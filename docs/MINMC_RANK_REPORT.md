# Side-separated minimum-MC rank report

## Conclusion

The side-separated rank hypothesis was tested through its single-pair gate. A
new bounded exact XOR-AND backend solved and independently verified 29 of the
30 deduplicated factors, but the resulting three-ancilla pebbling gate still
fails for most factors. The full rank oracle was therefore not attempted.

## Backend and inventory

`src/rank_factor_inventory.py` verified all three ten-term bases against the
exact target and recorded 30 deduplicated six-variable functions in
`artifacts/rank_factor_inventory.json`. The supplied Pareto factorization was
restored only after this exact check.

The new scalar backend is `src/minmc_xag.py`: a bounded Z3 search over XAGs
whose AND inputs and output are arbitrary XORs of constants, six inputs, and
earlier AND nodes. It searched 0..6 AND nodes with a 15-second solver timeout
per bound and wrote `artifacts/minmc_factor_cache.json`. Independent integer
truth-table evaluation verified every returned model: **29/30** unique
functions solved; the unresolved function is truth table `17997355542380544`.
This is a bounded exact result, not a proof that the unresolved function needs
more than six ANDs.

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

The genuine bounded-minMC models were then compiled by
`src/minmc_rank_pair.py` using the same explicit three-live-value pebbling
constraint. Only one complete Pareto pair was pebbleable: term 7 measured
x **69 depth / 65 CX**, y **55 / 47**, parallel compute **69 / 112**, and the
full compute–CZ–uncompute block **139 depth / 215 CX**, width 18. The other
available models failed the exact two-scratch cleanup search; one pair was
also unavailable because it used the unresolved factor above. Thus minimum
AND count alone did not translate into a cheaper reversible circuit.

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
minimum-MC/XAG database or improve the bounded SAT models with a reversible
cost objective and a pebble-aware synthesis constraint. The immediate
decision gate is to find a single complete pair below roughly 450 depth; the
measured 139-depth block clears that local gate, but the failure rate and
215-CX cost mean a ten-term oracle is not yet justified. Repeating the
current formula/XAG backend, basis search, or generic global cleanup is not
justified by these measurements.

Finally, `src/gl10_actual_search.py` ran an 80-step bounded GL(10,2)
transvection search from each of the three known ten-term bases, compiling
and serializing every candidate before scoring it. The best scores were
779/736 for `pair_terms`, 795/754 for `rank_terms`, and 803/751 for
`rank_mc_pareto_terms` (depth/CX). No candidate improved the trusted
779-depth pair baseline, so the basis lever is closed under this search
budget.

The remaining dirty-workspace prototype, `src/dirty_esop_pair.py`, computes
each ESOP factor directly into clean output wires using relative-phase MCX
blocks, then applies the exact inverse. It is correct on all 4096 basis
inputs, but the complete pair oracle measures **2156 depth / 1346 CX / width
18**. Avoiding the clean-pebble failure through direct ESOP therefore does
not provide a competitive primitive.

As a follow-up, `src/pebble_xag.py` searched a chain-restricted XAG family in
which each AND node depends on the immediately preceding AND node. This is a
more pebble-friendly dependency shape, but it is not expressive enough to
solve the challenge cheaply: it solved 29/30 factors, while the corresponding
pair compiler produced only 5/10 complete pairs in each basis. The measured
partial pair-depth sums were 771 (`pair_terms`), 744 (`rank_terms`), and 793
(`rank_mc_pareto_terms`) before counting missing terms. Consequently this
route is also closed for the current 531-depth target.
