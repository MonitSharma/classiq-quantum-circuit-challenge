# Phase-edge retention search

## Result

The dynamic-retention architecture is feasible and materially improves the
independent-edge phase-pebble baseline, but it does not approach the
protected depth-531 oracle. The complete retained oracle is exhaustively
verified at **depth 1818 / 2070 CX / width 18**.

The best term-7 schedule is **202 / 223 CX**, down from **728 / 683 CX**.
Term 6 is **186 / 182 CX**, down from **563 / 502 CX**. Both use all six
ancillas at peak and emit all required phase edges.

## Search and measurements

`src/phase_retention.py` tracks live nonlinear XAG nodes and an emitted-edge
mask. It emits every currently available commuting diagonal edge, permits
dependency-valid recomputation, and uses one six-ancilla pool. It ran five
endpoint-retention greedy policies, beam widths 64/256/1024, 500 local-order
trials for term 6, 2000 local-order trials for term 7, and a one-million-state
bound for pooled pebble moves.

The complete before/after table is in
`artifacts/phase_retention_pair_metrics.json`; structural instrumentation is
in `artifacts/phase_retention_structure.json`; the durable search log is
`artifacts/phase_retention_progress.jsonl`.

| term | edges | old depth/CX | retained depth/CX | scheduler |
|---:|---:|---:|---:|---|
| 0 | 2 | 218 / 190 | 192 / 140 | beam-1024 |
| 1 | 8 | 243 / 243 | 162 / 173 | greedy row |
| 2 | 8 | 311 / 357 | 240 / 271 | greedy shared |
| 3 | 6 | 275 / 325 | 165 / 209 | greedy row |
| 4 | 1 | 232 / 297 | 307 / 333 | beam-256 |
| 5 | 5 | 175 / 178 | 142 / 140 | greedy row |
| 6 | 12 | 563 / 502 | **186 / 182** | greedy row |
| 7 | 35 | 728 / 683 | **202 / 223** | beam-64 |
| 8 | 4 | 225 / 275 | 182 / 215 | greedy shared |
| 9 | 6 | 255 / 270 | 149 / 194 | greedy row |

The selected pair depths sum to 1927 before full-circuit transpiler cleanup.
The best of 100 complete term-order permutations was
`[5, 4, 2, 6, 9, 1, 7, 8, 0, 3]`.

## Verification

The final candidate is `artifacts/phase_retention_rank_mc_ordered.qasm`; its
exact report is `artifacts/phase_retention_rank_mc_ordered.exhaustive.json`.
The report SHA matches the QASM and records all 4096 clean-ancilla basis
inputs, zero ancilla leakage, preserved coordinates, and width 18.

## Conclusion and next path

Retention removes most repeated nonlinear compute/uncompute work. The
remaining cost is transient affine parity synthesis and repeated phase-edge
interaction/rebasing, especially for terms with many affine root
constituents. The next step is co-designing alternative XAG representations
with cross-term node retention, rather than independently scheduling each
term. This is a strong intermediate result, not a new challenge best.
