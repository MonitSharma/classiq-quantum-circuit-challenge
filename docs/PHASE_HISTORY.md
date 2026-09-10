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

## Next experiment

The next search should use cumulative-history membership as its primary
objective, generate wire-disjoint RCCX layers with bounded proposal counts,
and track actual `u3`/`cx` depth for promising forward trajectories. It must
preserve checkpoints and write new artifacts under `artifacts/phase_history/`.
