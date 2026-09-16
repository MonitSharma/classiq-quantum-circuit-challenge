# Post-190 joint storage recursive campaign

Date: 2026-09-16

Research question: can the x14+y13 nonlinear witnesses be scheduled into two
nonlinear stages on 18 wires once storage, dirty-target replacement, and
invertible affine frames are modeled exactly?

## Endpoint audit

The exact protected endpoint is
`[x0,x1,x2,x4 XOR x5,y0,y1,y2,y5]`. This is confirmed by the existing
composition and semantic-register code, the corrected-v2 storage model, and
the regression test that evaluates every coefficient vector. The earlier
`two_stage_oracle.py` raw-bit convention is provenance for a different
architecture and must not be silently substituted. Artifact:
`artifacts/post190_joint_endpoint_audit_v1/report.json`.

## Corrected affine-rank convention

Semantic coordinate bit 0 is the constant function. The campaign now computes
necessary storage rank in the quotient by that constant direction. This makes
`f` and `f XOR 1` rank-equivalent. The filter is necessary only; it does not
prove storage reachability or UNSAT.

## Exact fixed-schedule result

Command: `.venv/bin/python src/post190_joint_18wire_storage_sat.py
--timeout-ms 30000 --outdir artifacts/post190_joint_18wire_storage_v2`.

Result: `UNSAT` in 0.424566 seconds for candidate-0/candidate-0 and the
fixed schedule `[6,6,6,6,3]`, using the 40-bit semantic basis, six explicit
invertible affine frames, dirty-target updates, and literal endpoint rows.
This is a fixed schedule/model statement only; it does not close the schedule
family or the 32-pair portfolio.

With the corrected quotient filter, that particular schedule is necessary-
filter-infeasible at batch 2. This is a filter observation, not a second
independent SAT proof.

## Schedule census

`src/post190_joint_storage_census_v4.py` performs exact memoized topological
counting for all 35 ordered nonempty width patterns (27 nodes, five batches,
each width at most six). The total-only run completed in 28.09 seconds and is
saved in `artifacts/post190_joint_storage_census_v4_total/census.json`.

The five priority patterns and their quotient-rank necessary survivors are:

| widths | legal schedules | rank survivors |
|---|---:|---:|
| 6,6,6,6,3 | 3,944,524 | 2,786,240 |
| 6,6,6,5,4 | 10,235,839 | 7,172,159 |
| 6,6,5,6,4 | 8,207,149 | 6,085,848 |
| 6,5,6,6,4 | 7,063,012 | 6,123,118 |
| 5,6,6,6,4 | 6,415,779 | 5,488,106 |

These large survivor populations show that the corrected rank filter does not
close the architecture. The full 35-pattern rank census was launched behind
`src/run_bounded.py` with a 180-second external deadline. It returned
`EXTERNAL_TIMEOUT` in
`artifacts/post190_joint_storage_census_v4_rank_wall.json`; no family
conclusion is drawn from that timeout.

## Current decision

Status: `SOLVER_BARRIER`, not architecture closure. The exact fixed model has
a negative result, but the schedule family remains large and the symbolic
family SAT model has not yet been validated. The next bounded experiment is a
symbolic schedule-family model, beginning with the five priority width
patterns, using an external deadline and positive-control validation against
the corrected fixed model. A SAT result would require replay verification;
timeouts remain `UNKNOWN`.

The protected `artifacts/185/` package was not modified. No claim is made of a
sub-185 or rank-one oracle.
