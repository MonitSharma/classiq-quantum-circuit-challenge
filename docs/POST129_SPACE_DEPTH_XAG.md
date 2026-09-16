# POST129: storage-aware XAG campaign

Date: September 16, 2026. Protected best remains **185 / 854 / 18**;
`artifacts/185/` was not modified. This campaign audits existing exact XAGs
for a six-nonlinear-value storage target. It produced no native oracle or
leaderboard result.

## Phase-0 inventory

`src/post129_space_depth_xag.py` evaluated every discovered `.xag` using the
repository's exact 4,096-point XAG semantics and saved
`artifacts/post129_space_depth_xag/xag_inventory.json`.

The inventory contains 140 parseable graphs, including 10 exact logo graphs.
The exact candidates span 62–97 ANDs and multiplicative depth 6–9. The
recomputed no-recompute live estimates are 17–25 nonlinear values, not six:

| Candidate | ANDs | MD | Level widths | Live estimate | No-recompute screen |
| --- | ---: | ---: | --- | ---: | ---: |
| shared_balance | 81 | 6 | 26,22,14,12,6,1 | 19 | 25 |
| advanced_round4 | 62 | 8 | 15,11,12,10,7,4,2,1 | 19 | 17 |
| advanced_round2 | 65 | 7 | 16,12,12,11,8,4,2 | 22 | 20 |
| advanced_shared_rank | 65 | 8 | 15,12,13,11,9,3,1,1 | 20 | 21 |
| advanced_nist_sub45 | 62 | 8 | 16,11,12,10,7,3,2,1 | 17 | 18 |

The no-recompute values are heuristic topological screens, not impossibility
proofs. Affine operands are analyzed as full nonlinear dependency sets; they
are not reduced to only two parent nodes.

## Bounded six-pebble screen

`src/post129_pebble.py` implements reversible compute/uncompute search with a
hard six-live-node cap, automatic phase marking for output nonlinear roots,
recomputation, and dependency-safe uncompute. Searches capped at 20,000
expanded states for `shared_balance`, `advanced_round4`, and `advanced_round2`
all returned `UNKNOWN`, not UNSAT. Their reports are under
`artifacts/post129_space_depth_xag/pebble/`.

This is useful triage but not a closure: the state limit was reached before a
proof or schedule. The next exact improvement would need a stronger heuristic
or an externally bounded solver model, followed by affine-frame materialization.
No physical schedule, QASM, or exhaustive verification was attempted because
no six-pebble schedule was found.

## Next decision

The existing graphs are not immediately competitive under the six-pebble
model. The promising route is a new XAG synthesis objective that includes
nonlinear liveness, output-root phase timing, affine-control exposure, and
batch depth during synthesis. Minimum AND count alone should not be optimized.
Any candidate must still be lowered to exactly 18 wires and verified with the
standalone U3/CX exhaustive workflow before being called an improvement.

