# Phase-history synthesis

This branch explores the phase oracle directly. The required action is

\[
|x,y,0^6\rangle \mapsto (-1)^{logo(x,y)}|x,y,0^6\rangle,
\]

not necessarily computation of `logo(x,y)` into a final classical wire.

## Construction

If a reversible forward trajectory `G` temporarily places Boolean function
`W` on a physical wire, a `Z` at that point contributes
`(-1)^W`. After the complete trajectory is reversed, the computational state
is restored and the phase remains. Therefore the target is sufficient if

`TARGET ∈ span_GF(2)({W_j^(t)} ∪ {1})`.

`src/phase_history_search.py` stores each 4096-bit truth table as a Python
integer, maintains an incremental GF(2) basis, and retains provenance for each
independent signal. The exact decomposition is back-solved before any circuit
is constructed. Duplicate truth tables do not increase rank; their occurrence
locations are retained for later tap scheduling.

`src/build_phase_history_oracle.py` emits the forward primitive sequence, the
selected historical `Z` taps, and the exact inverse sequence. Boolean history
membership is only a necessary construction step: every serialized candidate
must still pass `src/exhaustive_verify.py`.

## Initial trajectory audit

The audit replayed the preserved destructive histories without judging them by
their old final-state affine residual. Ranks include the constant-one signal.
The fused-tail history was reconstructed from its builder and includes its
four RC3X operations.

| History | Primitive gates | Forward depth | Forward CX | Unique signals | Historical rank | Logo in span? |
|---|---:|---:|---:|---:|---:|---|
| seed 42, depth-59 candidate | 12 RCCX | 59 | 32 | 25 | 23 | No |
| seed 42, depth-73 candidate | 18 RCCX | 73 | 46 | 31 | 25 | No |
| seed 1, depth-84 candidate | 18 RCCX | 84 | 48 | 31 | 28 | No |
| fused-tail candidate | 20 RCCX + 4 RC3X | 102 | 72 | 32 | 30 | No |

Reports are in
`artifacts/phase_history/existing_trajectory_audit/`. These negative results
are expected: they validate the new exact machinery and show that the first
shallow basins do not already contain a solution.

## Verification status

The incremental basis, nonlinear history identity, duplicate handling,
complement/global-phase handling, full 4096-point semantic replay, and a
three-qubit forward/Z-tap/inverse quantum round trip are covered by
`tests/test_phase_history.py`.

No full-logo phase-history candidate has yet entered the exact historical span.
The protected baseline remains untouched at depth 524, 950 CX, SHA
`7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147`.

The first bounded single-RCCX history searches (beam 16, proposal limit 48,
eight layers, seeds 1 and 42) both ended without membership. Their best
historical rank was 19 and their greedy target residual was 917; the exact
Gaussian remainder remained 1097. These are diagnostic negative results, not
evidence against phase-history synthesis. They show that the first serial
proposal heuristic is not finding sufficiently diverse target-correlated
nonlinear signals.

The native calibration confirms that disjoint RCCX layers are genuinely
parallel under the required transpilation settings:

| Disjoint RCCX count | Serialized depth | CX |
|---:|---:|---:|
| 1 | 7 | 3 |
| 2 | 7 | 6 |
| 3 | 7 | 9 |
| 4 | 7 | 12 |
| 5 | 7 | 15 |
| 6 | 7 | 18 |

The calibration is saved in
`artifacts/phase_history/rccx_layer_calibration.json`. A first two-wide,
five-layer search reached rank 22 at estimated forward depth 35, but did not
enter the logo span. Its checkpointed result is under
`artifacts/phase_history/parallel_seed7_b8_l5/`.

RC3X calibration is also recorded in
`artifacts/phase_history/rcccx_layer_calibration.json`: one through four
disjoint RC3X gates each serialize to depth 13, with 6, 12, 18, and 24 CX
gates respectively. A mixed RCCX/RC3X beam run (beam 24, six layers, three-way
parallel proposals, seed 303) stayed within estimated forward depth 78 but
ended at rank 23 with greedy residual 1073 and no exact membership. Its
checkpointed result is under
`artifacts/phase_history/search_mixed_seed303_b24_l6_p3/`.

## ANF diagnostic

`src/multiplicative_depth_analysis.py` computes the exact 12-variable ANF by
the Möbius transform. It is a structural diagnostic only; it does not compile
the terms individually. The report is saved at
`artifacts/phase_history/logo_anf.json` and records degree 12 with 886
nonconstant terms. A future multiplicative-depth/XAG tool should consume this
structure as proposal guidance while the phase-history engine remains the
actual oracle-construction path.

The exact ten rank-decomposition product truth tables are also used as
structural hints in the beam score. The first bounded RCCX/RC3X hinted run
found zero of those products exactly in the historical span, so proximity to
known products alone is insufficient; the result is retained under
`artifacts/phase_history/hinted_seed505_b8_l4/`.

Affine-control RCCX moves are now represented with their internal CX/RCCX/CX
history, preserving intermediate provenance. The bounded affine-enabled run
at `artifacts/phase_history/affine_seed606_b8_l6/` reached rank 19 at
estimated forward depth 48. It brought one historical signal within eight
truth-table bits of a rank product, but exact target membership still failed.

Destructive X/CX proposals are now included as cheap affine moves, exposing
complemented literals and arbitrary linear forms. The first mixed X/CX/RCCX/
RC3X run (`artifacts/phase_history/linear_mixed_seed707_b8_l8/`) reached rank
29 at estimated depth 88, but did not enter the exact target span. Its depth
slightly exceeds the preferred 85-depth forward budget because affine-control
macros cost nine native layers; it is retained as a diagnostic rather than a
candidate.

## Exact end-to-end baseline

`src/build_rank_phase_history_seed.py` uses the repository's exact ESOP
predicate builder to expose each of the ten verified rank products on q14,
deposits a Z phase, and clears each block. The serialized standalone QASM is
`artifacts/phase_history/rank_product_seed.qasm`; its matching exhaustive
report is `rank_product_seed.exhaustive.json`. It passed all 4096 basis inputs
with zero ancilla leakage, depth 2380, and 1531 CX gates. The exact QASM SHA is
`710127eeb72bebf54cb4494698089e25592252ab0a0982abc5cf09c3dc85e2d9`.

This is a correctness baseline, not an improvement: independently computing
and clearing each rank factor is far too expensive. The useful result is that
the phase-history constructor and verification workflow are validated on the
full logo, so subsequent optimization can safely attack sharing and cleanup.

Two alternative exact ten-product decompositions were run through the same
builder and exhaustive verifier. `rank_mc_pareto_terms.json` produced depth
2402 / 1529 CX with SHA
`8a69e458b35adf7d564b1adf63be44214b82e46396f3a1ce4328a74490c072a2`, while
`pair_terms.json` produced depth 2424 / 1560 CX with SHA
`ac64f4eff163220d141b9cf416d3cb301092796ad9ef74e3e4c5ce1e6155d168`.
Both reports check all 4096 inputs with zero ancilla leakage; neither improves
the 2380-depth `rank_terms` baseline.

An accumulator experiment kept q14 live across all ten products and used
relative-phase dirty-MCX synthesis to preserve it while computing q12/q13.
The exact QASM is `artifacts/phase_history/rank_accumulator_seed.qasm`; it
passed all 4096 inputs with zero leakage, but serialized to depth 7355 / 4031
CX (SHA
`094b603b18f93aa800b00bd5916b5dac882f0cd3d7cbc881c40da3c537af6158`). The
conceptual sharing gain is overwhelmed by dirty-MCX lowering cost, so this
implementation is closed as a negative direction.

Bounded pytket post-processing (`FullPeepholeOptimise` and `CliffordSimp`) was
also applied to the 2380-depth seed. The best fresh QASM,
`artifacts/phase_history/rank_product_seed_tket.qasm`, remained depth 2380
but reduced CX to 1525. It passed exhaustive verification with zero ancilla
leakage; SHA
`9e5dc7c1c5b3559ae23c0119ec61564d1b9736e469efb1a3b6ee852a03b06882`.
Because depth did not improve, generic pytket post-processing is closed for
this seed.

## Phase-block ordering search

The ten rank-product phase blocks commute logically, but their serialized
ordering affects local cancellation during Qiskit's `u3`/`cx` lowering. The
ordering search in `src/search_phase_term_order.py` tested 120 deterministic
permutations and found the order `[0, 9, 5, 6, 7, 2, 1, 8, 4, 3]`. The exact
candidate is `artifacts/phase_history/rank_product_order_search_120.qasm`,
with matching metrics and exhaustive report. It passed all 4096 inputs with
zero ancilla leakage at depth 2359 and 1520 CX gates; its QASM SHA is
`baed794d3294e652e12516f94b79692021d45e69d8e03de2a694eb43a28d2883`.

This improves the phase-history baseline from depth 2380 / 1531 CX to
2359 / 1520 CX, but remains well above the protected depth-524 circuit. It is
therefore a verified experimental improvement, not a new repository best.

A broader 1000-permutation run found a further exact improvement. The best
order was `[2, 7, 4, 3, 8, 9, 5, 6, 1, 0]`; its candidate is
`artifacts/phase_history/rank_product_order_search_1000.qasm`. The matching
exhaustive report checks all 4096 inputs, restores all ancillas, and records
depth 2348 / 1513 CX with SHA
`c96ecd26f8f5e7a6fca1d42d51b8806476f3e01bc5113ce7eb98b302a711e384`.
This remains an experimental phase-history result, not a replacement for the
protected depth-524 artifact.

A 2000-permutation continuation found order `[8, 4, 3, 0, 2, 9, 5, 7, 6, 1]`.
The fresh QASM `artifacts/phase_history/rank_product_order_search_2000.qasm`
was exhaustively verified on all 4096 inputs with zero ancilla leakage at
depth 2342 / 1513 CX; its SHA is
`cf88a76d99dbeb5262676b29d1dbcac551d85076b05942325dd31844da002254`.
This is a native-cancellation improvement within the exact rank-product
baseline, but it is still far above the <180 research target.

As a controlled comparison, fresh exhaustive reports were generated for the
pre-existing shared-XAG phase artifact and its rank-basis variant. Both pass
all 4096 inputs with zero ancilla leakage: `artifacts/xag_phase.qasm` measures
depth 905 / 795 CX (SHA
`3aaa4ef5f8681b1895cb82c32fdd084bce588915366b665769d253bed3a28abf`), while
`artifacts/xag_basis_rank_False.qasm` measures depth 1390 / 1039 CX (SHA
`3a1d1d9b5b10ce6ad68124393858e0b458cbf62007363dc5411b4a6abaaa901a`). These
are validation records for an older route, not new candidates.

## Protected-circuit native retranspilation control

To check whether the current best was an artifact of one transpiler seed,
`src/search_protected_retranspile.py` reserialized the protected QASM with 48
deterministic seeds, always using `qubits_initially_zero=False`. Every run
produced depth 524 / 950 CX. The selected fresh output was exhaustively
verified on all 4096 inputs and had the exact protected SHA
`7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147`; the
files were byte-identical. This closes native seed variation as a source of
an immediate improvement without touching the protected artifact.

## Six-way parallel higher-order beam diagnostic

The capped search at
`artifacts/phase_history/search_seed1001_b8_l8_p6/` explicitly allowed up to
six wire-disjoint nonlinear proposals per layer, including RC3X and affine
macros. With beam 8, proposal limit 16, and eight layers, it reached estimated
forward depth 84 and historical rank 22, but exact target membership remained
false; product- and factor-hint coverage were both zero. The checkpointed
frontier is retained as a reproducible negative diagnostic, not as an oracle.

A broader continuation at
`artifacts/phase_history/search_seed1002_b16_l10_p6/` used beam 16, proposal
limit 24, six-way layers, RC3X proposals, and ten layers. It completed all
checkpoints at estimated forward depth 102 and historical rank 25, but exact
target membership and both rank-product/factor hint coverage remained zero.
This confirms that simply widening the parallel higher-order beam does not
solve the target under the current proposal/scoring model.

The search engine now also supports `--rank-first`, which makes cumulative
historical rank the primary pre-membership objective instead of the heuristic
Hamming residual. The controlled run at
`artifacts/phase_history/search_seed1003_rankfirst_b16_l10_p6/` reached rank
26 at estimated forward depth 106, but exact target membership and both
rank-product/factor hint coverage remained zero. This separates a scoring
stagnation issue from the deeper proposal-space limitation.

## Next experiment

The cumulative-history objective, provenance recovery, exact oracle builder,
parallel-layer calibration, and bounded beam machinery are now in place. The
six-way and rank-first runs show that repeating the same local RCCX/RC3X
proposal family does not generate even one exact rank-product factor. The next
meaningful search must therefore add target-guided nonlinear proposals from a
shared XAG/AND graph or an equivalent factor synthesizer, while preserving the
same exact span-membership and exhaustive-verification gates. Do not spend
additional runs on wider copies of the closed local beam until that proposal
source exists.
