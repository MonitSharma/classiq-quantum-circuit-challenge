# Joint storage exhaustive-v3 schedule expansion

Date: 2026-09-16

## Scope

This run extends the corrected storage-aware free-frame model without claiming
an architecture-wide result. The target is candidate-0 x candidate-0, with 27
fixed nonlinear nodes, five ordered nonempty batches, batch width at most six,
arbitrary invertible affine frames, dirty targets, and literal endpoint rows.

The schedule generator enumerates sorted node tuples per batch, respects every
nonlinear dependency, and deduplicates by the ordered tuple-of-tuples schedule.
The new `rank_capacity_profile()` applies only the proved necessary rank
condition

```text
2k - c <= 18 - d
max(d, c+k) <= d' <= min(d+k, c+18-2k)
```

It is a pruning filter, not a physical reachability proof.

## Execution result

The first attempt to solve even a 100-schedule prefix with a 200 ms Z3 timeout
was stopped after the external interactive bound because the current model
construction itself dominates: six 18×18 inverse-constrained frames are
materialized before Z3's internal timeout can meaningfully limit solving. The
interrupted run produced no schedule-level conclusion and no cases are counted
as UNSAT from it.

The previously completed corrected-v2 artifacts remain the valid finite
evidence: twelve fixed cases returned UNSAT, including candidate-0 with the
original schedule and eleven additional fixed schedules/pairs. Those results
remain fixed-model statements only.

## Decision

This is a **solver-barrier result**, not a portfolio closure. The next safe
engineering step is to factor/cache the frame constraints or invoke each case
through `src/run_bounded.py` with a real external deadline, then expand the
schedule set. No claim is made about all schedules, all 32 witness pairs, or
the existence of a native <=137 oracle.

Regression coverage includes the schedule generator, exact five-batch result,
all 32 capacity-passing witness pairs, and the necessary rank-capacity filter.
