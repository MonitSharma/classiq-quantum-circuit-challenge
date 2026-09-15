# POST190 whole-schedule closure

Date: 2026-09-15

Decision: **WHOLE-SCHEDULE CLOSED** for scaling.

This was the final bounded experiment for coordinated, non-monotone mutation of
the existing shallow destructive semantic schedule. It did not reopen the
structured-XAG, phase-weaving, class-relabeling, or protected-code searches.

## Integrity and implementation checks

- `artifacts/190/` was not modified.
- The scheduler now treats CX as a two-wire operation and RCCX as a three-wire
  operation. Legal-layer and cache tests pass (`3 passed`).
- Historical gate lists were imported and packed into legal layers. However,
  replaying the saved `gates` fields with the current initial truth tables gives
  exact affine residual 683 for both nominal depth-59 and depth-84 records,
  rather than metadata values 447 and 379. Those metadata values are retained
  as historical claims, not used as current replay baselines.
- Complete elite schedules were transpiled in the `u3`/`cx` basis with
  `qubits_initially_zero=False`; all remained 18-wire circuits.

## Cache benchmark

The benchmark prebuilt the initial truth tables and compared the same replay
workload. Speedups (full replay / suffix replay) were:

| basin | first changed at | 0 | 25% | 50% | 75% | end |
|---|---:|---:|---:|---:|---:|---:|
| nominal depth 59 | layer | 1.01x | 1.36x | 1.97x | 2.71x | 28.58x |
| nominal depth 84 | layer | 0.97x | 1.55x | 2.16x | 4.97x | 37.08x |

This validates the suffix-cache mechanism, but does not itself indicate a
better search landscape.

## Matched ablation

For each imported basin, each policy used the same eight seeds, 0.45 seconds
per run, 3,000-iteration cap, and temperature 1000/cooling .999. The proxy was
used during search; exact affine distance was computed on every selected elite.

| basin | policy | median exact residual | best exact residual | best native depth/CX |
|---|---|---:|---:|---:|
| nominal depth 59 | tail-only | 565 | 565 | 43 / 35 |
| nominal depth 59 | one global gate | 683 | 537 | 44 / 34 |
| nominal depth 59 | full interior | 658 | 537 | 51 / 34 |
| nominal depth 84 | tail-only | 565 | 565 | 61 / 67 |
| nominal depth 84 | one global gate | 683 | 565 | 66 / 50 |
| nominal depth 84 | full interior | 683 | 565 | 54 / 60 |

Accepted uphill moves were approximately 31.7–59.7% across the six groups, so
the negative result is not explained by a frozen Metropolis chain. No policy
recovered or approached the historical metadata residuals, and no exact
classifier was found. The best current replay result, residual 537, is not a
structural improvement and has no submission significance.

## Positive controls and conclusion

The imported schedules themselves were used as semantic/native controls. Their
current replay controls produced residual 683 and native depths 45/66, which
confirms the serialization mismatch above. Since the controls do not reproduce
their claimed historical states, they cannot support a positive optimizer
result.

The whole-schedule family is therefore closed: this bounded coordinated
interior mutation experiment did not show a material improvement over the
protected best or a credible route to an exact affine classifier. No further
compute is justified under this family, and no new architecture is promoted.

Artifacts:

- `artifacts/post190_whole_schedule_closure/report.json`
- `src/post190_whole_schedule.py`
- `src/run_post190_whole_schedule_closure.py`
- `tests/test_post190_whole_schedule.py`
