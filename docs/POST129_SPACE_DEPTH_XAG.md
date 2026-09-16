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
recomputation, and dependency-safe reversible toggles. A node may be
uncomputed whenever its own predecessors are live; live successors do not
block parent removal. Searches capped at 20,000
expanded states for `shared_balance`, `advanced_round4`, and `advanced_round2`
all returned `UNKNOWN`, not UNSAT. Their reports are under
`artifacts/post129_space_depth_xag/pebble/`.

This is useful triage but not a closure: the state limit was reached before a
proof or schedule. The next exact improvement would need a stronger heuristic
or an externally bounded solver model, followed by affine-frame materialization.
No physical schedule, QASM, or exhaustive verification was attempted because
no six-pebble schedule was found.

The five-batch physical-row co-synthesis implementation
(`src/post137_joint_encoder_cosynth.py`) now searches variable RCCX topology
over the two 9-row side states and ranks candidates lexicographically as
`exactness → affine residual → nonlinear batch count → peak liveness → toggle
count`. It uses CEGIS: a small side-input sample is screened, failing points
are added, and the candidate is replayed on all 64 inputs before it can become
the full-domain incumbent. Seed137 at a short bounded run remains non-exact
(combined full residual 127 in the latest one-second screen; the earlier
three-second pilot reached 116). These are semantic residuals, not circuit
depths.

Exact affine-span candidates can now be materialized as physical RCCX batches
plus affine X/CNOT frames in the 9-wire encoder view, mapped to the actual
18-wire x/y layout. `compose_preserved_kernel()` composes both exact encoders
with the recorded kernel and routes the result through the repository's native
U3/CX lowering, whose transpilation uses `qubits_initially_zero=False`. No
exact candidate has reached that gate, so no full-oracle QASM or verification
report was created in this screen.

The next bounded step replaced independent random walks with a width-limited
beam over variable physical RCCX batches, followed by joint x/y pairing and
the same CEGIS replay. A two-second seed231 screen reduced the combined full
residual to 92 (from 122–127 in the earlier one-second probes), still without
an exact encoder. This is a search-quality improvement, not a native-depth
result.

The following solver step adds an explicit six-slot gate to the beam: after
each batch, rows outside the affine span of the six inputs plus constant are
counted as nonlinear storage, and paths above six are pruned before x/y joint
pairing. A two-second seed239 run stayed feasible throughout (x peak 6, y
peak 4) and reached combined residual 96. This establishes storage-feasible
search progress, but not an exact encoder or a native-depth result.

## Constrained solver checkpoint

The existing bounded Z3 reversible-register backend was screened at five
nonlinear stages, variable controls/targets, and a nominal 59-layer encoder
ceiling. With eight sampled inputs it produced provisional models, but both x
and y failed all 64-input replay checks. With all 64 inputs, both sides timed
out after two seconds. These outcomes are `UNKNOWN`/timeout, not UNSAT and not
evidence that five batches are impossible. The next solver improvement should
carry the beam incumbent into the constraint model and encode the six-slot
storage/liveness bound explicitly.

The CEGIS failure extractor was corrected during this integration to use the
support of the full-domain affine residual. A one-point residual is always zero
when the constant row is available, so per-point residual checks are not valid
counterexamples. After correction, the seeded one-second x/y solver screens
returned `UNKNOWN` after receiving 45 and 37 constraints, respectively.

`src/post137_frame_storage_sat.py` is the next refinement: it gives each
five-batch beam topology explicit invertible 9x9 affine matrices and
translations, solves sampled output equations, and replays extracted frames
over all 64 inputs. In the first bounded screen, x timed out and y was SAT on
the sample but replayed with nonlinear storage peak 9, so it was rejected by
the six-slot gate. Frame placement still needs an in-model storage constraint.

That constraint is now in the model. After every affine frame and nonlinear
batch, each row is either proven (over the current sample) to be in the
six-input-plus-constant affine span or counted as nonlinear; a cardinality
constraint permits at most six nonlinear rows. The first stricter screen timed
out for both x and y, producing no sample-SAT overflow model. This is still
`UNKNOWN`, not UNSAT.

## Next decision

The existing graphs are not immediately competitive under the six-pebble
model. The next bounded runs should use affine budgets 8, 10, 12, and 14 and
apply the strict gates: an encoder at most 49 native layers is built into the
full oracle immediately; 50–60 is still built and measured; no exact encoder
by budget 14 is recorded as a meaningful negative result. Minimum AND count
alone should not be optimized. Any candidate must still be lowered to exactly
18 wires and exhaustively verified before being called an improvement.
