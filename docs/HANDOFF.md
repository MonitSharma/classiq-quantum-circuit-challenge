# Continuation handoff

## September 16: selective recovery implemented and measured

Read `POST185_SELECTIVE_RECOVERY.md` before repeating the earlier proposals.
`src/post185_selective_recovery.py` implements inverse dependency cones,
release using current logical controls, one-AND input recovery, and paid
affine destination preparation. Input 9 at the three-root checkpoint recovers
with two RCCX gates, increasing forward depth 40 to 44. The four-root milestone
is now 65 forward layers (112 including compiled restoration); it is only a
partial phase operator. The five-root milestone is already 233 compiled layers.
Thirty-six bounded trials found no complete oracle; protected185 is unchanged.
Residual completion degree is 8 at the new milestones, still not a cheap
diagonal finish. Nineteen focused tests pass. A cap check after phase deposition
is fixed; the old 140-cap target-form probes actually reached 141 and are flagged.
All jobs are finished. Do not scale the same root-count beam blindly.

## September 16: latest phase-rooted destructive campaign

Read `POST129_PHASE_ROOTED_XAG.md` first. The latest user request supersedes
the side-encoder and six-pebble follow-ups below: compile backward from phase
roots of exact `advanced_round4` on all 18 mutable physical wires. Implemented
`src/post129_phase_rooted_xag.py`; 165 bounded destructive trials, including
resumed and recovery probes, produced no complete logo trajectory. The compact
checkpoint deposits three of 11 roots in 40 forward layers; full rollback
reaches four in 109. These are partial traces, not oracle depths. Complete
affine-preserving controls pass exhaustive verification but cost 1440–1525
layers. Protected **185 / 854 / 18** is unchanged. Next: dependency-aware
multi-step recovery from the three-root checkpoint, not another control sweep.
Eleven focused tests pass. No optimization jobs or monitoring are scheduled.

## September 16: POST129 storage-aware XAG campaign

Read `POST129_SPACE_DEPTH_XAG.md`. The phase-0 inventory evaluated 140 `.xag`
files exactly and found 10 exact logo graphs. Existing exact candidates need
17–25 nonlinear live values in the no-recompute screen, versus the six-value
18-wire target. Bounded six-pebble searches for shared_balance,
advanced_round4, and advanced_round2 reached their 20,000-state limits and
returned UNKNOWN, not UNSAT. No native candidate was produced. The next XAG
campaign must co-synthesize liveness, affine exposure, phase-root timing and
batch depth; do not infer infeasibility from these cutoffs.

The corrected pebble implementation now permits dependency-legal parent
removal while a child remains live. Recomputed no-recompute screens are
slightly more conservative. The five-batch physical-row CEGIS is in
`src/post137_joint_encoder_cosynth.py`; it adds full-domain counterexamples,
uses the requested lexicographic score, and exposes affine-frame lowering plus
preserved-kernel composition. Short affine-budget 8/10/12/14 probes found no
exact encoder, so this remains a semantic screen rather than a native
candidate.

The latest beam refinement now prunes any path exceeding six nonlinear
physical storage rows after a batch. Seed239 stayed within the limit (x peak
6, y peak 4) and reached combined residual 96, but remains non-exact.

The five-stage bounded Z3 backend was screened separately: sampled models did
not survive 64-input replay, while all-64-input runs timed out at two seconds
for both sides. Treat this as solver timeout/unknown, not a negative proof.
`src/post137_seeded_solver.py` now carries full-domain residual-support
counterexamples from storage-feasible beam paths into that backend. A short
seeded screen returned UNKNOWN for both sides after 45/37 constraints.

The affine-frame SAT refinement in `src/post137_frame_storage_sat.py` uses
explicit invertible 9x9 matrices and translations. Its first bounded screen
timed out for x; y was sample-SAT but failed replay storage (peak 9), so no
model was promoted.

New steering prioritizes residual phase completion. The audit
`src/post185_phase_completion_search.py` checks the saved rooted checkpoints;
all three need degree-9 current-wire phase completion, with no exact degree-1
through degree-4 representation. Report:
`artifacts/post185_phase_completion_v1/report.json`.
The six-slot condition is now enforced inside the affine-frame SAT model after
every frame and batch. The first stricter screen timed out for both x and y;
no storage-invalid model was promoted, and the result remains UNKNOWN.

## September 16: attached deep-research assessment

Read `POST185_DEEP_RESEARCH_REPORT.md`. The attached report independently
profiles and replays the protected185 QASM, but produced no new circuit. Its
useful conclusion is that fixed-endpoint reordering has only a restricted
174-layer floor and that the next high-upside experiment is a history-aware
destructive 18-wire compiler: phase taps may use transient wire truth tables,
not only final midpoint wires. This is a hypothesis and campaign direction,
not a global lower bound or a rank-one result. Web citations, live leaderboard
claims and challenge-date claims in the attachment remain unvalidated here.
The saved-trajectory audit is complete and negative: see
`artifacts/direct_e_v2_history_audit/report.json` and
`src/direct_e_history_audit.py`. The strongest seeded 7/18 run reaches
historical rank39 but does not contain the target. Next: fix/retain the shared
primitive timeline, then integrate the existing phase-history engine with
Direct-E v2 rather than reimplementing it.
The first bounded v3 smoke test is now implemented in
`src/direct_e_v3_history.py`. It combines selective Z/CZ history features with
the existing Direct-E mutation engine; a 3-second seeded 7/18 run evaluated
93 states, reached historical rank50 and decoder distance933, and found no
exact hit. This is an integration smoke result, not evidence of a useful
search gradient. Transformed-coordinate XAG proposal guidance remains
pending.

The transformed guidance dictionary is now generated by
`src/build_transformed_xag_guidance.py` and saved as
`artifacts/direct_e_transformed_xag_guidance.json`: 1,750 exact node truth
tables from the 264-term transformed target, multiplicative depth4 and
estimated live width270. A first 3-second guided 7/18 smoke run reached
decoder distance1097 (worse than the unguided933 smoke) with no exact hit.
The current control-pair proposal heuristic should be redesigned before any
long campaign.

After decoder and layer-aware guidance fixes, matched 3-second seeded 7/18
smokes reached distance1001 for both unguided and guided variants. Unguided
evaluated77 states; guided evaluated1 because its shortlist/full-score path is
expensive. The earlier933/1097 smoke scores are superseded. No long campaign
is justified until proposal throughput and semantic gain improve.

## September 16: corrected deep-research implementation

Read `POST185_DESTRUCTIVE_XAG_IMPLEMENTATION.md` and the rewritten
`POST185_AND_NETWORK_ROUTE.md`. Leaderboard architecture identification,
universal six-live-node limits, degree/cascade impossibility, and width-from-MD
claims were unsupported and are superseded. The old note is archived.
Implemented physical destructive XAG lowering, paid affine exposure, intermediate
Z/CZ phase taps and literal inverse; synthetic no-clean-ancilla dirty-coordinate
cases pass. Full logo searches remain incomplete. Fixed joint storage solver
operand remapping, x4 XOR x5 endpoint, all-zero initial rows, XOR replay,
schedule replay, and inverse checks. The original0.13-second UNSAT is invalid;
the corrected fixed schedule separately returns UNSAT in0.42 seconds. Broader
fixed-schedule probes remain scoped, not family-wide conclusions. Protected
185/854/18 is unchanged.30 focused/regression tests pass and all8 saved physical
traces independently replay; no jobs remain running. The old212-toggle pebbler now has full4096-input quantum
verification at23 wires/692 depth/728 CX, explicitly width-ineligible. Exact
six-pebble feasibility at212 toggles timed out. Rank one remains unfinished.

## September 16: measured floor, with joint 18-wire route still open

Read `docs/POST185_ARCHITECTURE_FLOOR.md`. Decomposed the protected oracle into
`load ‖ kernel ‖ unload` and measured the spectra each block pays for: loader
Walsh support 174/175, kernel integer-lift support 90. The `r + 2c <= n` layer
bound caps a nine-wire loader at three rotations per layer and the eight-wire
kernel at 8/3, giving a 174.4 floor for this representation of these codes
against the packaged 185; it is not a universal two-stage lower bound.
Annealing the labels against that bound (`src/post185_schedule_floor.py`) reaches
148.5 at `S=(116,110)`, `M=126`, but building those codes gives 240, not 148:
sparse spectra lower the CX-walk hit rate as fast as they lower the rotation
count. Four built families, all exhaustively verified, are 226 (protected), 239,
240 and 258. Three closures: a loader-aware label anneal finds nothing better
than the protected codes (16 runs, all 200-225 against their 190.7); trading
loaded bits for raw kernel wires multiplies the kernel spectrum by eight
(90 to 749) for a nine-layer loader saving; and a Toffoli/ANF loader needs 40-44
nonlinear monomials per side, far above the 78-layer rotation loader. A new
balanced stage-assignment loader verifies exactly but only ties the fixed
skeleton. Protected 185/854/18 is unchanged and `artifacts/185/` was not
touched. The joint 18-wire x14+y13 route remains open: its exact 27-AND
witnesses admit five capacity-optimal batches across all 32 retained pairs.
See `docs/POST190_JOINT_18WIRE_FEASIBILITY.md`; storage-aware free-frame
feasibility is the next priority. Six focused tests pass. No submission or rank
check.

## September 16: Direct-E v2 and Quasar assessment

Read `docs/POST185_DIRECT_E_V2.md`. Reproduced the user's ten-operation global
affine transform from886 to264 ANF terms, with a saved inverse-checked witness.
The existing RCCX already compiles to7 layers; the old9-layer direct-template
number was a loose bound. Implemented free physical layers, parallel midpoint
phase masks, exact nearest-parity fitness, paid affine seeding and SAT repairs.
46,109 proposals under conditional135/137 budgets found no exact classifier;
best still misses657 of4096 inputs. Quasar runs, but its verified result is
187/853, rescheduled to186/853. Its decimal parser needed a recorded precision
fix. Protected185/854/18 remains unchanged.15 focused/regression tests pass.
A matched no-prefix control ends at827 errors versus657 with the affine seed.
No jobs remain running. No new submission or rank-one result.

## September16: audit-before-testing literature search

Read `docs/POST185_METHOD_SEARCH.md` before proposing another method. Audited
existing code/docs against current primary research, then implemented two
concrete gaps: larger SAT phase-network synthesis and CZ-frame direction
optimization.105 six/seven-wire SAT windows found one isolated5→4-layer
replacement, but full depth stays185.9,600 CZ-direction proposals plus exact
joint direction models likewise do not beat185 after global scheduling.
Eight focused tests pass.57 complete output files have matching-hash exhaustive
reports; protected185/854/18 remains unchanged. All jobs finished; no submission.
Timeouts and fixed-model optima are not global depth bounds. New sources:
`src/post185_sat_phase_blocks.py`, `src/post185_cz_orientation.py`.

## September 16: side-research audit and five-variable loaders

Read `docs/POST185_FIVE_ADDRESS_AUDIT.md`. Reproduced five-variable encoders,
including an x loader at 60 layers, and searched labels jointly with nine/
ten-wire phase kernels. Tested both-axis and asymmetric variants, then direct
reachable-state LP phase completions: 16,592 label proposals, twelve full
QASMs passing all 4,096 inputs. Best in this experimental family is265/911;
protected185/854/18 is unchanged. The side note's156-layer floor is not proved,
and the saved protected kernel is38 layers/87 CX, not29. Nine focused tests
pass. Reusable script `src/post185_five_address.py`; saved witnesses include
coefficients and complete descriptors. All jobs finished; no submission.

## Latest depth-focused follow-up: 185 remains protected

Read `docs/POST185_DEPTH_CAMPAIGN.md`. The user emphasized depth over CX count.
Completed multi-rewrite walks, 600 dirty-mediator rewrites, 400 restored-label
compilations, 290 strict 184-layer tests, 420 deadline-aware local windows,
and joint phase placement/global scheduling. No verified sub-185 circuit was
found. Neutral retiming reduces a critical-gate proxy, not actual depth.
The phase-placement model reaches fixed-model optimum185 with 867 occurrence
choices; this is not a global depth lower bound. Three solver cases and one
four-wire window remain unresolved at their limits. Thirty-one focused tests
pass, and `artifacts/185/package_audit.json` confirms matching QASM, reports,
QMOD, and identical replay. Preserve 185/854/18 and prioritize larger structural
depth changes rather than CX tie-breakers. No submission or monitor was made.
The final PhasePoly composition gives verified186/854, not a gain. All jobs
from this continuation are finished.

## September 15: verified 185 / 854 / 18 through new CNOT identities

Current protected best is **185 depth / 854 CX / 18 qubits**, `artifacts/185/`,
SHA `ef933bc786bc25feb1fbd618fc8c45a0bdc8dce43879aacfcc6042daaca5bfc8`.
Read `docs/POST186_CNOT_REWRITES.md`. Three exact CNOT rewrites, native fusion,
and scheduling improve 186/855 to 185/854, U3 763. All 4,096 inputs, five dense
states, gate-matching QMOD, and identical-hash replay pass. Use the new builder
`src/build_bridge_oracle.py --package artifacts/185 --outdir <new-directory>`;
the rescheduling-only builder cannot apply the identities. Twenty-one focused
tests pass. Exact three-wire search (12,000 attempts) and context-scored four/
five-wire phase networks (150/160 completed windows) did not improve their
input circuits. The optional beam step limit records nonconvergence safely.
The user has now emphasized **depth over CNOT savings**: allow extra CX and
focus subsequent experiments on shorter depth. No submission or live-rank
check was made; the screenshot's 137-depth leader remains ahead.

## September 15: verified 186 / 855 / 18 through phase reordering

Current protected best is **186 depth / 855 CX / 18 qubits**, `artifacts/186/`,
SHA `5e7f8f165928e965cc47d5b697def0681a79aa6432b8d94302374fd071f25ac6`.
Read `docs/POST188_PHASE_REORDERING.md`. Checked H/Rz conversion, PhasePoly
rotation-level reordering, native fusion, and exact scheduling improve 188/855
to 186/855, with 770 U3 gates. All 4,096 inputs and five dense states pass;
literal QMOD matches all 1,625 gates. Replay needs no external optimizer:
`src/build_rescheduled_oracle.py --package artifacts/186 --outdir <new-directory>`.
Fresh replay matches the hash and passes all inputs. Six focused tests pass.
Joint modular loaders, sparse-code/kernel combinations, and Pauli synthesis
did not beat this result. The old balanced-code blanket floor-77 claim was
not reproduced; actual alternative loaders are 71–76, but their complete
oracles are slower. A previous 193/853 circuit now reaches 188/853, still behind
186/855 on depth. Fixed-graph optima are not global oracle bounds. All earlier
packages remain preserved. No submission or live-rank check was performed;
the screenshot's leader is 137/561. Rank one remains unfinished.
Final split-phase, native-inverse, and nonlinear-candidate checks did not beat
186; the nonlinear alternative improves 200 to 195. All jobs are finished;
no background optimization or leaderboard monitor was created.

## September 15: verified 188 / 855 / 18 through commuting-gate scheduling

Current protected best is **188 depth / 855 CX / 18 qubits**, `artifacts/188/`,
SHA `f8f7e73ad2d48daa31a29a354e2287347b90e59d460f9e7d271495850635e46e`.
Read `docs/POST190_COMMUTING_SCHEDULE.md`. A conservative commutation DAG,
13-circuit portfolio, exact CP-SAT scheduling, and native U3 fusion improved
the previous 191/855 source to 188/855. All 4,096 inputs and five dense states
pass; the QMOD matches every gate. Deterministic replay:
`src/build_rescheduled_oracle.py --package artifacts/188 --outdir <new-directory>`.
Its saved schedule is required; the old permuted-package builder alone does
not reproduce it. The original notebook and 190 package remain preserved.
Four focused tests pass. Exact scheduling optima apply only to each fixed
commutation graph. The exact 190 file's busiest wire has 176 gates, correcting
the older 181 count. No new 50-layer encoder or sub-140 circuit was built.
The user's screenshot shows a 137/561 leader; no live rank or submission was
checked. Rank one remains unfinished. All jobs finished, no automation created.
Earlier "current best" entries below are historical checkpoints.

## True joint-stage campaign: verified generator, no new logo encoder

Read `docs/POST190_JOINT_STAGE_CAMPAIGN.md`. Implemented simultaneous width2/3
control selection, exact H and quotient enumeration, full-span semantic search,
and physical replay. All5,494 first successors of the saved Y prefix certify
at least4 further stages are needed from that prefix in the fixed-product model.
The extended four-stage search reached456,886 full spans and timed out without
completion; this is not a global impossibility result. Protected190/857/18 is
unchanged. Synthetic joint encoder15/24/9 is a positive control only. Focused
suite23 passes; full suite174 passes plus the existing phase-factorization test
failure. All campaign jobs finished.


## Information-space campaign: pruning flaw measured, no new complete encoder

Read `docs/POST190_INFORMATION_SPACE_CAMPAIGN.md`. Legacy span dedup discarded
1,108 of7,215 colliding states with better measured future exposure/materialization
cost. Added full512-input semantics, physical/Pareto retention, affine frames,
semantic hyperplane search, packed moves and saved-prefix repair. Bounded A–E,
X14/Y13 and5–7-stage tests found no complete encoder. Best saved prefixes still
have2/4 goals.16 focused tests pass. Protected190/857/18 remains unchanged;
partial44/61-depth circuits are not usable loaders. All campaign jobs finished.


## Seeded register campaign: exact x14/y13, no new native best

Read `docs/POST190_SEEDED_REGISTER_CAMPAIGN.md`. Independently recreated x15→14
ANDs, and improved y14→13 by broader NIST affine enumeration. Both match all64
inputs; levels are x[8,3,3], y[6,4,3]. Added exact-function mutable nine-wire
scheduling with free output placement and spectator mixing. No complete
sub77 encoder emerged from the bounded searches. Free-output composition
control196/866/18 passes all4096 inputs; it is not a gain. Six focused tests
pass, all new jobs finished, protected190/857/18 unchanged.


## Correction: sub-135 remains an unbuilt target

Read `docs/POST190_CAMPAIGN_AUDIT.md` before the campaign claims below.
The 62-node Boolean network and 5131-depth oracle are supported by current files,
but no 48–50-depth encoder or sub-135 oracle exists in the inspected artifacts.
The new pebbler preserves all12 inputs; it does not implement coordinate reuse.
The seven-times-RCCX-batch-count lower bound is invalid under native interleaving.
Best remains190/857/18. Next: seeded nine-wire lowering with free output placement.


## Direct in-place Boolean compiler and 30,048 NIST 6-cut database

See `docs/POST190_SUB137_CAMPAIGN.md`. Executed both requested components:
1. **Direct Boolean in-place quantum oracle:** Completed `src/xag_to_inplace_layers.py` and `src/test_continuous_oracle.py`, realizing $E \to Z_{17} \to E^\dagger$. Standalone transpiled QASM circuits generated with `qubits_initially_zero=False`:
   - `artifacts/sub137_round1/oracle.qasm`: Depth 5,337, CX 4,076, `max_error = 1.81e-13`, `ancilla_error = 0.0`.
   - `artifacts/sub137_round1/oracle_continuous.qasm`: Depth 5,131, CX 3,859, `max_error = 1.66e-13`, `ancilla_error = 0.0`.
   Both pass `src/exhaustive_verify.py` on all 4,096 basis states, proving that relative phases from RCCX cancel identically with zero ancilla leakage. Replay:
   ```bash
   PYTHONPATH=src .venv/bin/python src/test_continuous_oracle.py
   ```
2. **NIST 6-cut database & Mockturtle integration:** Built `tools/md_synth/build_full_minmc6_db.cpp` and `tools/md_synth/find_missing_6cut.cpp`, populating `artifacts/post190_nist_catalog/nist_6cut_db.txt` with **30,048 canonical functions**. Fixed Mockturtle's `xag_minmc2.hpp` `load_from_file` parser and recompiled `tools/mockturtle/build/md_synth_advanced` with ABC SAT and Percy. Cut rewriting on `advanced_round4.xag` ran with 30,048 functions loaded and rewrote cuts without crashes. Replay:
   ```bash
   tools/mockturtle/build/md_synth_advanced artifacts/multiplicative_depth/logo_truth.hex artifacts/multiplicative_depth/optimized/advanced_round4.xag advanced artifacts/multiplicative_depth/optimized/advanced_nist_sub45.xag
   ```
3. **Register bottleneck & parallel NIST solution:** Sequential 5-pebble Bennett uncomputation on 62 ANDs produces ~5,100 depth due to repeated uncomputation across 10 roots. Replacing the 77-layer multiplexer loaders with parallel execution of the NIST 15-AND / 14-AND coordinate witnesses (`x_merged_witness.json` and `y_merged_witness.json`) would require verified roughly50-layer encoders to approach135 depth; those encoders have not been built. Protected baseline remains **190/857/18** in `artifacts/190/`.

## Y-fold audit and disk-only encoding observation

See `docs/POST190_Y_FOLD_AUDIT.md`. Reproduced 95/71/11 and added native quantum
verification. Corrected interval length (25), raw descriptor widths (5/6/7),
and overbroad impossibility claims. A disk-only y5-band fold is 74/56/9 and
matches both disk predicates on all 4096 pairs; it is not a full-logo circuit.
Deriving radius from folded x permits three-bit r-1 with zero as empty, but
its loader and original-y comparisons remain unbuilt/unmeasured. Best190 intact.


## Joint reversible free-label search

See `docs/POST190_JOINT_REVERSIBLE.md`. Added actual nine-wire synthesis with
free four-bit class labels, optional within-class splitting, and fresh-kernel
composition from actual encoder outputs. Six bounded probes found no full
witness; two sampled SAT circuits failed the full domain and were rejected.
Composition control is 201/866/18, verified on all 4096 inputs, not a gain.
Three focused tests pass. New jobs finished; protected 190/857/18 is unchanged.


## Literature-guided search and NIST witnesses

See `docs/POST190_LITERATURE_CATALOG.md`. Four normal-form SAT probes timed out
without a conclusion. The public NIST catalogue supplied five-AND witnesses
for all six protected code bits, each checked on all 64 inputs. Selected
witnesses merge to 15 ANDs (x) / 14 (y). Two individual predicates lower into
nine wires at 124/127 layers; four exhaust only the restricted scheduler model.
No full-oracle improvement: protected 190/857/18 and SHA are unchanged.
Two SAT-control tests and one catalogue regression test pass. New jobs finished.


## Register-aware implementation completed

See `docs/POST190_REGISTER_IMPLEMENTATION.md`. Added finite three-ancilla
register-span scheduling, quantum-checked lowering, direct nine-wire reversible
search, and full protected-kernel composition with exhaustive verification.
A synthetic four-internal-node/seven-AND witness fits nine wires in eight
nonlinear toggles (75 encoder layers); this is NOT a logo improvement.
The bounded 48/70-layer direct searches produced no full witness; a partial
SAT circuit failed 47 inputs and was rejected. Four focused tests pass and
full baseline replay matches the protected SHA exactly. Best stays 190/857.
All new runs finished; external searches were left untouched.


## Stronger fixed-label bound and improved witness lowering

Read `docs/POST190_XAG_DEGREE_CERTIFICATE.md`. The protected labels require
**at least six ANDs per side**, by rank-three degree>=5 output components and
the scalar degree bound. With AND-depth<=3, at least **seven** are required.
All six running scratchpad target functions were checked against the protected
labels. No running process was touched; liveness could not be inspected.
The supplied synthetic k=3 witness now lowers to **24 layers/22 CX/9 wires**,
versus its naive 41/42/14; its full synthetic oracle passes all 64 inputs.
This is a compiler improvement, NOT a new logo circuit. 190/857 stands.


## Side-analysis audit and next Boolean probe

Read `docs/POST190_SIDE_ANALYSIS_AUDIT.md` before using the attached side
analysis as a closure map. Reproduced counterexamples invalidate universal
six-rotations-per-layer and 64-rotations-per-six-input-predicate claims.
The full logo matrix has GF(2) rank ten. Annealing and private leaderboard CX
counts do not prove the claimed algorithm families or global minima.
A free-label shared-XAG probe at 4–6 ANDs per side returned six timeouts;
no witness, UNSAT certificate, or new oracle. Positive-control test passes.
190/857 remains protected. All runs finished.


## Latest bounded follow-up: nonlinear phases and local windows

See `docs/POST190_NONLINEAR_AND_WINDOWS.md`. Best remains **190/857/18**.
A 673-case nonlinear/LP screen reduced phase support to 51 but the best full
alternative was 200/859, exhaustively verified. 240 local window trials did not
improve 190. Corrected x-tag and inverse-Walsh/phase-unit errors in the older
reachable-lift experiment; corrected eight-start search retained 63 terms.
Old runs using those erroneous helpers do not establish architectural limits.
Four focused tests pass; all runs finished and protected QASM hash unchanged.


Latest structural research: read [POST190_NEW_ARCHITECTURES.md](POST190_NEW_ARCHITECTURES.md).
The 190 best is unchanged. A direct compute/Z/uncompute template has a
**conditional 139-layer budget**, but no satisfying full-logo circuit was found.
The 16-sample witness failed 2,047 full inputs; 32-sample Z3 and a bounded
CaDiCaL attempt timed out. Do not present the template as a sub-140 circuit.
New degree-four split-class codes are verified, but are not shallow encoders;
their selected kernel has 255 principal phase terms. Mixed-coordinate screens
found no new qualifying partition. Three focused tests pass; no jobs remain running.

Leaderboard leader **142**; target sub-140 then rank one. Verified best is now
**190 depth / 857 CX / 18 qubits**, `artifacts/190/`, SHA
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`. All 4,096
basis inputs pass at 7.78e-15 with zero ancilla error, five dense random states
pass at 2.16e-16, and `src/build_permuted_oracle_package.py --package
artifacts/190` replays the package to the same SHA. The 196, 193/853, 192 and 191
packages are preserved.

This round was **193 -> 190**, from widening the endpoint search's configuration
grid rather than from any structural change; see
[`POST193_ENDPOINT_GRID.md`](POST193_ENDPOINT_GRID.md).

Profile the circuit before optimising it. The loaders finish between layers 73
and 77, all eight kernel wires arrive at 75-77, the kernel spans about 36, and
`max_w (forward[w] + span + inverse[mapping[w]])` reproduces the compiled depth
exactly. So the oracle is `77 + span + 77`, the busiest wire's 181 gate slots are
*not* binding, and only the span is reducible. The asymmetric forward/inverse
loader search, rerun against the shipped kernel over 16,113 gauge-compatible
pairs, predicts a minimum composed depth equal to whatever the span already gives
-- it cannot help until the span moves.

Two beam options existed but had never been combined with the relaxed endpoint
contract: `horizon`, which ranks beam states by committed depth plus an
optimistic remainder, and `fill`, which allows wider CX layers. Adding both, and
recomputing arrival times from the loaders the package actually ships rather than
the ones the earlier sweep assumed, produced 192, then 191, then 190. Every
winner sat on the previous grid's boundary, so the grid was pushed until it
stopped paying; the useful region is beams 96-128, branch 18-22, alpha 5-7,
timew 1.0-1.4, horizon 1.5-2.2, fill 2-3, and 190 appears there at roughly one
run in a hundred.

The loaders remain at their own floor: for the codes this package uses, Walsh
support is 174 and 175, the frame-cost bound returns 77, and the compiled loaders
are 77. The kernel's gate-occupancy bound is near 29 against a span of 36, so the
span still has room. Nothing here touches
[`ADDRESS_WIDTH_CLOSURE.md`](ADDRESS_WIDTH_CLOSURE.md): sub-140 still needs a
different descriptor, not a better schedule.

## Latest: 193 depth, CX reduced to 853

The current best package is `artifacts/193_cx853/`: **193 / 853 / 18**, SHA
`4dbd4993f7d1e807b5ae2908f9580d70070f247a4496140b858f08c95ce82709`.
**Depth did not improve in this continuation.** The new phase beam accounts for
free ancilla ordering during final selection, and loader seeds are now 298/506.
Read [POST193_CX_REFINEMENT.md](POST193_CX_REFINEMENT.md). All 4,096 inputs and
five dense states pass; QMOD matches; fourteen targeted tests pass.
Compiler replay uses `src/build_permuted_oracle_package.py --package artifacts/193_cx853`.
Older verified packages remain intact. No jobs or monitors are running.

## September 14: verified improvement to 193

Current best is **193 depth / 857 CX / 18 qubits**, packaged with a matching
literal QMOD in `artifacts/193/`. SHA
`5c00b23d9ea061b8b3062caac17ae2de0ab8457a4705ecc3eea8c1eed49a1bec`.
Read [POST193_RESEARCH.md](POST193_RESEARCH.md) first. The 196 package is preserved.
All 4,096 inputs and five dense random states pass; replay matches the exact
SHA; eleven targeted tests pass. No submission or rank-one result is claimed.

The gain combines a new 63-term phase representation with kernel restoration
up to a physical permutation of the clean ancillas and a matching rewired
uncompute. **The new kernel alone is not diagonal.** Use
`src/build_two_stage_193.py` and its saved recipe; do not substitute it into the
old symmetric builder without the uncompute mapping. No jobs remain running.

## Earlier 196-depth checkpoint and address-width analysis

Leaderboard leader **142**; target sub-140 then rank one. Verified best remains
**196 / 858 / 18**, `artifacts/196/`, SHA
`63333fade2e7e38c9a4edf333888c26bdac234c04e955fd6a624c0ea6e714c30`.

**The strongest measurement in this repository is address width.** A three-output
lookup costs **77** layers at six address bits, **48** at five, **33** at four.
Every earlier search moved Walsh terms around *inside* a six-address lookup,
where 77 is provably the frame design's floor; narrowing the address is worth 29
layers per side, far more than any scheduling gain.

**And it is now closed for a four-wire descriptor**, which is what the eight-wire
kernel requires. See [`ADDRESS_WIDTH_CLOSURE.md`](ADDRESS_WIDTH_CLOSURE.md). Split
`z = (A, R)` into `k` address bits and a residual; the most general descriptor is
`(p address bits, f_A(R), m clean bits)` with `p + (6-k) + m = 4`, where `f_A` may
be a different invertible map per address, produced by the lookup itself and
written onto the dirty coordinate wires. Only different-address pairs can collide,
so the whole question is whether the address patterns fall into at most
`2^(k-2)` equivalence classes:

| k | budget | row needs | column needs |
|---:|---:|---:|---:|
| 4 | 4 | 12 | 11 |
| 5 | 8 | 14 | 13 |
| 6 | 16 | 11 | 11 |

Only `k = 6` fits. For a two-bit residual the maps ran over the full affine
group, and `|AGL(2,2)| = 24 = 4!`, so every permutation of the four residual
states was allowed -- the widest per-address freedom there is -- and the counts
do not move. This closes the pre-map route *and* the dirty-lookup-output route at
once, because the criterion is stated on the descriptor rather than on a
construction. `tests/test_post196_address_width.py` keeps it honest.

Screen any future proposal with that criterion first: it is one line, and it is
where the last three routes died. Widening to a five-wire descriptor does admit
`k = 5`, but then roughly 28 of 32 descriptor values are used per side, the kernel
loses its don't-care freedom, and the measured outcome of that regime was 711
terms at 382 layers.

Leaderboard leader **142**; user target sub-100 and rank one. Verified best is
**196 / 858 / 18**, `artifacts/196/`, SHA
`63333fade2e7e38c9a4edf333888c26bdac234c04e955fd6a624c0ea6e714c30`.

Read [`POST196_FLOOR_AUDIT.md`](POST196_FLOOR_AUDIT.md),
[`ARITHMETIC_MIDDLE_PROBE.md`](ARITHMETIC_MIDDLE_PROBE.md) and
[`NONLINEAR_LOADER_PROBE.md`](NONLINEAR_LOADER_PROBE.md) first; then
[`POST196_SLACK_PROFILE.md`](POST196_SLACK_PROFILE.md), which is the current
picture and supersedes the estimates in
[`POST196_FLOOR_ANALYSIS.md`](POST196_FLOOR_ANALYSIS.md).

**Where the 196 layers are, measured rather than modelled.** The loader's 77 is
exactly its own floor: the binding host needs all eight low masks in a frame, so
it performs 8 rotations plus a length-8 closed tour = 16 operations = 16 layers,
four frames give 64, plus 13 layers of frame skeleton. The compiled loader hits
77 on the nose, at 81.7% occupancy, with its busiest control wire carrying 56 of
the 193 CX. **There is no loader slack.** All reachable slack is the kernel: 43
against an occupancy bound of 24-31.

**The frame bound was loose and is now tightened.** The audit's counterexample --
six hosts each needing low masks {0,1}, where low wire 0 alone needs twelve CX --
returned 4 against a true 13. A per-wire contention term now closes that case.
Rescoring every saved candidate with the tightened bound **retracts the earlier
"balanced codes beat 77" result**: they all return 77, which is why they had
measured 70-72 and 225-233 rather than the predicted 61-68.

Closed this round, with the nature of each closure stated: affine relabelling of
the loaded code bits is **exhaustive** over its 10,752-element group and every
map gives 77/90; no rank-2 quadratic splits either side's classes four/four, so
the cheapest route to a two-output lookup is shut; the cheapest class-splitting
bit at all has Walsh support 23 (row) and 18 (column), over all cell subsets.
Kernel scheduling resisted A*-style ranking, wider CX layers, high hit weights,
and an anneal over integer lifts scored by compiled depth (which found 46, worse
than 43).

So this staging's floor is `2 * 77 + 31 = 185`, conditional on the frame
skeleton, the current code and the current kernel representation. 142 is below
it. Nothing here proves a general limit, but every scheduling avenue tried is
now exhausted, and the remaining candidates are structural: break the 16-layer
binding host, or avoid the four-frame skeleton.

Latest construction experiment: nonlinear coordinate preconditioning screened
12,007 tables and compiled a correct **204 / 891 / 18** oracle, which loses to
196. All 4,096 inputs pass. See [NONLINEAR_LOADER_PROBE.md](NONLINEAR_LOADER_PROBE.md)
for the search scope and exact-file report. Seven targeted tests pass; no jobs
remain running. The protected 196 circuit is unchanged.

Leaderboard: the reported leader is **142**; the user's target is sub-100 and rank
one. The verified local best is **196 depth / 858 CX / 18 qubits**,
`artifacts/196/`, SHA `63333fade2e7e38c9a4edf333888c26bdac234c04e955fd6a624c0ea6e714c30`,
rebuilt deterministically by `src/build_two_stage_196.py`.

**Read [`POST196_FLOOR_AUDIT.md`](POST196_FLOOR_AUDIT.md) and
[`ARITHMETIC_MIDDLE_PROBE.md`](ARITHMETIC_MIDDLE_PROBE.md) before
[`POST196_FLOOR_ANALYSIS.md`](POST196_FLOOR_ANALYSIS.md).** The analysis file
previously claimed that the two-stage architecture was closed and that 142 was
excluded. Both claims were wrong and are now corrected in place:

* its frame cost function is a *lower bound*, not the schedule cost. The audit's
  counterexample -- six hosts each needing low masks {0, 1}, where low wire 0
  alone needs twelve CX -- returned 4 against a true 13. A per-wire contention
  term has been added (`max_k sum_hosts 2 * [subset touches bit k]`, valid because
  a closed tour from 0 toggles each visited bit an even nonzero number of times);
  it now returns 12 there, and `tests/test_post196_frame_bound.py` keeps it honest;
* the claimed general kernel floor `3 * T / 8` is false -- eight singleton
  parities are depth 1, not 3. Use `ceil((T + 2 * max(0, T - n)) / n)`;
* occupancy is 71.0% (858 CX, 789 U3, 2,505 slots, bound 140), not 65%;
* annealing certifies nothing about global optimality over labels or `GL(6,2)`.

What survives is weaker but still useful: the bound is 77 on the recorded codes
and the compiled loaders achieve 77, so those codes are optimal *within this
frame design*; and no annealed label set or sampled wire basis beat them.

The literal-radius-plus-band hybrid has a resource obstacle, but this does not
close all hybrids. Unused radius patterns can encode empty and rectangle-only
modes in three loaded bits, with code zero carrying exceptions distinguished by
y5. Decoding those modes and handling the exceptions still costs gates. No
competitive complete implementation has been demonstrated. See the encoding
example in [NONLINEAR_LOADER_PROBE.md](NONLINEAR_LOADER_PROBE.md).

Leaderboard: the reported leader is **142**; the user's target is sub-100 and rank
one. The verified local best is **196 depth / 858 CX / 18 qubits**,
`artifacts/196/`, SHA `63333fade2e7e38c9a4edf333888c26bdac234c04e955fd6a624c0ea6e714c30`,
rebuilt deterministically by `src/build_two_stage_196.py`.

Latest measured arithmetic result: a four-bit phase comparator with two clean
helpers improves from 65 to **25** layers, or 69 to **36** with an enable bit.
Both exact serialized components pass all their input states. They are not
logo oracles. See [ARITHMETIC_MIDDLE_PROBE.md](ARITHMETIC_MIDDLE_PROBE.md) for
artifacts, the remaining integration costs, and a new frame-model audit.

The frame model is not an exact scheduler: a six-host counterexample predicts
4 but needs at least 12 CX layers on one low wire. Annealing does not certify
an optimum over labels or GL(6,2). The 196 best is verified; the claimed
architecture-wide closure is not.


The leaderboard's lower CX counts motivate searching for fewer-gate
constructions, but do not identify the private submissions' algorithms.
Arithmetic is one hypothesis. The earlier roughly 85-layer estimate for its
middle was not a measured full implementation; the verified 25/36-layer
comparator components leave loading, geometry guards, and exceptions unresolved.

Current milestone: **sub-140 first**, then further reduction toward rank one. See [SUB140_SEARCH.md](SUB140_SEARCH.md) for the new Boolean, quadratic-feature, and conditional-loading experiments. Best verified full circuit remains 196 / 858 / 18.

Leaderboard update, September 13: the reported leader is now **142 depth**, and the
user's target is **sub-100**. The verified local best is **196 depth / 858 CX / 18
qubits**, `artifacts/196/`, with exhaustive verification, five dense checks, a
matching literal QMOD and a deterministic rebuild
(`src/build_two_stage_196.py`). SHA `63333fade2e7e38c9a4edf333888c26bdac234c04e955fd6a624c0ea6e714c30`.

The latest floor analysis has been audited: its universal exclusion of 142 is
not proved. The frontier search omitted free completion bits (a real 97-term
row code improves to 94 terms), and its bounded shortlists cannot establish an
all-code frontier. Correct occupancy is 71.0%, with a 140-layer occupancy lower
bound for the existing gate multiset. See [POST196_FLOOR_AUDIT.md](POST196_FLOOR_AUDIT.md).
This does not produce a better oracle; avoid repeating old sweeps without a
new mechanism.

Latest objective: **sub-100 and rank one**. The 196-depth baseline has been independently reproduced and exhaustively rechecked. The leader observed in Safari is 142 / 557 / 18. Read [POST196_RESEARCH.md](POST196_RESEARCH.md) for the output-layout correctness fix and new bounded searches. No improved complete circuit or rank-one result is claimed.

Current best, September 13: **196 depth / 858 CX / 18 qubits**, `artifacts/196/`, exact-file exhaustive verification, five dense checks, matching literal QMOD, and a deterministic rebuild. SHA `63333fade2e7e38c9a4edf333888c26bdac234c04e955fd6a624c0ea6e714c30`. The gain is a beam-search schedule for the eight-wire phase kernel (66/123 -> 43/89) plus encoder-seed reselection; the class codes and integer lift are unchanged from `artifacts/218`. `docs/POST218_RESEARCH.md` records the improvement, the loader floor argument, and seven failed variants. Sub-180 and rank one remain unresolved; this is an intermediate result.

Historical best, September 13: **218 depth / 897 CX / 18 qubits**, `artifacts/218/`, exact-file exhaustive verification, dense checks, matching literal QMOD, and identical-hash kernel/oracle replay. SHA `3a685c32ea0d78637be1a575c91e6c7d13db0efdbf37a8f794fb44e7fb024a88`. Integer full-turn cube additions reduce the kernel from 69 to 66 layers. See `POST221_RESEARCH.md` and `artifacts/218/README.md`. Sub-180 and rank one remain unresolved; this is an intermediate result.

Previous best, September 13: **221 depth / 944 CX / 18 qubits**, `artifacts/221/`, matching literal QMOD and exact-file exhaustive verification. SHA `4f9fa6232930777426ac4f8118155780471f111c31435e7578175170035e313f`; fresh replay matches. Joint selection of relative-phase encoders (y seed 99, x seed 151) improves the complete circuit by one layer and one CX. All 221 Pareto timing combinations from 160 seeds per side were compiled; none beat 221. See `artifacts/221/README.md`. Sub-180 and rank one remain unfinished.

Previous best, September 13: **222 depth / 945 CX / 18 qubits**, `artifacts/222/`, matching QMOD and exact-file exhaustive verification. SHA `6c8ff19470da3d6550d1741d502065e1ace10c72cb4c9d62aa4683703a344031`; fresh replay matches. Read `POST224_REVIEW_AND_EXPERIMENTS.md` for the relative-phase boundary change, tested in-place witnesses, and corrections to proposed depth floors. Sub-180 remains unfinished.

Earlier best: **224 depth / 957 CX / 18 qubits**, `artifacts/224/`, with matching QMOD and exact-file exhaustive verification. SHA `14b9272a21fc9a8d47ce036daa2c45fe792e092f06078f3e7ad4dd14bb79371f`; fresh replay matches. See `POST258_RESEARCH.md` for the parity-assisted class codes and joint scheduling. Sub-180 remains unfinished.

Earlier tie-breaker update: `artifacts/243_cx951/` is verified at **243 depth / 951 CX / 18 qubits**, with matching QMOD. SHA `38f5948a44d21c923ae740e64b968336898448ee01a30e85d81c583fe3dff696`. It supersedes 243/971 by CX count only; sub-180 remains unfinished. See `POST258_RESEARCH.md` for the further structural tests.

## Earlier checkpoint: verified 243-depth two-stage oracle

The renewed sub-180 investigation now has a verified **243/971/18** oracle,
with a matching gate-level QMOD and independent dense checks in `artifacts/243/`.
See [POST258_RESEARCH.md](POST258_RESEARCH.md). SHA:
`adb3093877907683fd70dcf6bc3a4043f4b4dc2f6999ad118f8fc996d839f4f1`.
The prior 258 package is preserved. The successful change is a raw-coordinate-
assisted, four-bit-per-side class code: two loader stages, one eight-wire kernel.
An integer phase lift and per-wire scheduling reduced the kernel from 107 to
88 layers. All 4096 inputs and three dense states pass; replay matches the SHA.
Sub-180 and rank one remain unfinished. The user explicitly asked to continue
until a sub-180 method is found; this is an active optimization request, not a
handoff-only task. No background automation or leaderboard monitor is scheduled.

## Historical best: verified 258-depth distributed lookup oracle

September 12: active construction work reduced the verified best from 456 to
**258 depth / 1188 CX / 18 qubits**. See
[DISTRIBUTED_LOOKUP_258.md](DISTRIBUTED_LOOKUP_258.md). The protected package is
`artifacts/258/`, including exact QASM, exhaustive and independent dense
verification reports, matching gate-level QMOD, kernel, and replay recipe.
SHA: `b2a2e8ac6a6d7ee2c2e4ec11bcca4b4ba4fe54aab15b11c71236efcecdca3066`.

The successful changes distribute Walsh phases onto temporarily borrowed
coordinate wires, use explicit three-layer parity-basis transitions, carry
Gray-walk offsets across stages, and replace the old 27-layer kernel with an
exact 13-layer construction. Five focused tests pass and a fresh replay matches
the QASM SHA. This supersedes the older claims that the lookup construction or
27-layer kernel could not improve. The earlier notebook and verified circuits
remain intact. No new challenge submission was made; 183 and rank one remain
unfinished. No optimization processes or monitors are intentionally left running.

## Earlier September 12 depth-gap audit (historical)

The latest user request is renewed code analysis and help reaching the observed
183-depth leaderboard level; the older handoff-only task description is stale.
See [DEPTH_GAP_ANALYSIS_2026-09-12.md](DEPTH_GAP_ANALYSIS_2026-09-12.md).
The 456/1140 and 524/950 hashes and notebook metrics match. The 456 circuit has
a fixed-wire scheduling floor of 389 (q16 gate touches). A proof extends the
odd-population parity argument to a depth >=682 bound for X/CX/diagonal-only
circuits with six basis-state ancillas, **not general U3/CX circuits**.
Twelve default-code UCGate components verify but remain 127 depth each; no
full candidate or new best was produced. Safari displays 183/789 as leader
and Monit S. at rank 24, 524/950. No submission or background run was started.
The report explicitly corrects overbroad older claims of architectural
optimality; the 456 artifact was the best documented local oracle at that checkpoint.

## September 12 native v2 checkpoint: verified but too deep

The requested concrete encoder experiment produced a verified nine-qubit v2
encoder at **301 depth / 176 CX**, missing the roughly 31-depth checkpoint.
It screened 1,248 degree-5 code assignments and compiled 18 candidates. Six
focused tests pass and replay reproduces the exact QASM hash. This is a
negative result for the implemented split-code/ESOP lowering, not a general
encoder-depth bound. No full-oracle integration was attempted; the verified
456-depth best remains unchanged. See
[V2_NATIVE_CHECKPOINT_2026-09-12.md](V2_NATIVE_CHECKPOINT_2026-09-12.md).


## September 12 correction: degree-3 code route excluded for v2

The new complete split-class screen excludes three-bit degree-at-most-three
v2 level encodings, even allowing arbitrary classes to use multiple codes.
Fourteen split pairs fail linear constraints; the remaining pair is UNSAT in
two formulations/backends. The three independent checks pass. This supersedes
the suggestion that the degree-3 code route merely needs completion.
See [the reassessment](SUB180_REASSESSMENT_2026-09-12.md) for scope and evidence.
The best documented depth remains 456/1140; the sparse candidate is now
exhaustively verified at 472/1128 and is not an improvement. Sub-180 remains
unfinished. The 524 and 456 artifacts are both preserved.


## Level-encoder exact-enumeration checkpoint (September 11, 2026)

The challenge page was refreshed in Safari. It explicitly ranks by **depth
first**, with **CX count only as the tie-breaker**. The live top entries observed
there were 183/789, 188/451, 190/389, 191/374, and 195/432 (all width 18), so
the verified 456/1140 level circuit is a depth improvement over the protected
524/950 fallback but is not close to the current rank-1 score.

The first exact small-operand synthesizer is `src/level_encoder_search_exact.py`.
It enumerates all XORs of up to three current registers and complements, then
checks every resulting state for an exactly separating code triple before
residual ranking. A bounded `u1` run with beam 4 and nine AND layers reached
residual 21 after 47 seconds and found no replayable separating network. The
original stochastic search and all verified QASM artifacts are unchanged. This
is a search-policy checkpoint, not an impossibility result.

The serialized 456 QASM was also screened with 20 Qiskit transpiler seeds and
two pytket rewrite passes. The best remained **456/1140**; full peephole was
458/1140. These local cleanup routes are closed for now.

The complete cross-branch research index is [`METHOD_INDEX.md`](METHOD_INDEX.md).
It summarizes every method family, experiment, research reference, evidence
level, and closure decision; this handoff retains the operational details and
artifact-specific history.

Current research entry point: [September 9 literature and repository review](RESEARCH_REVIEW_2026-09-09.md). The protected best is **524/950/18**, hash checked again in `artifacts/research_structure_audit.json`. Safari's live leaderboard shows Daksh S. at 197/475 and “Monit S.” at rank 21 with 531/1020; historical “nothing submitted” statements below are stale. No upload was made during this review. The new report narrows several overbroad architectural claims and records exact selector/code-size and boundary-residual diagnostics. No new quantum best is claimed.

## Shared-address descriptor checkpoint (September 11, 2026)

The shared-address QROM hypothesis was reopened before circuit generation.
Exact quotienting gives 11 row classes and 11 column classes, so a binary
descriptor needs at least four bits per side. The all-16-label search records
a reachable-domain witness with 31 ANF terms, 154 literals, and degree 7,
using three unreachable-address completions; the old 86/366 result was
incomplete. This remains a mathematical screen, not a <=55-depth kernel or
an impossibility proof. Details are in `src/shared_address_descriptor.py`
and `artifacts/shared_address_descriptor/descriptor_report.json`.

## Shared-address and monomial-embedding checkpoint (September 11, 2026)

The shared-address QROM screen found 11 row and 11 column classes, requiring
4+4 descriptor bits. The reopened all-16-label screen has a reachable-domain
witness with 31 ANF terms, 154 literals, degree 7, using three unreachable
address completions; the old 86/366 result was incomplete. The follow-up
whole-register X/CX/RCCX beam allowed
arbitrary placement of four y-code bits and two garbage wires, but found no
exact boundary map in the completed four-primitive beam (best exact score 186/256).
Longer runs were stopped for throughput. These are
bounded closures of the tested descriptor and monomial families, not
impossibility proofs against every phase-tolerant traversal.

An audit corrected two implementation errors in the earlier comparator probe:
the semantic beam had initialized input wires as `1<<i` instead of 64-bit
truth signatures, and the y-loader had placed all three m bits on q13. The
corrected four-output ESOP probe is **555/359** on the clean-x slice, but its
corrected 4096-input reusable-loader check finds **3696 mismatches** because
the dirty MCX scratch is unsafe. Fixed-label
bucket multiplicities (x=25, y=20) rigorously rule out four code bits plus two
garbage bits on six wires. A new affine screen found rank-5 garbage projections
injective within every code bucket using the 3+3 ancilla split. See
`artifacts/comparator_oracle/three_plus_three_affine_screen.json`; this
positive resource result still needs native nonlinear lowering.

The focused 3+3 native lowering was then implemented for both y kernel
directions (28 and 35) and all overwrite choices. The generator now uses a
distinct kernel-orthogonal basis for k=35, checks care-set collisions, and
verifies all 64 raw mappings. The best exact encoder remains **1491 depth /
845 CX** (k=28, overwrite bit 1); k=35's best is 1504/866. This fails the
<=70 criterion, so x-side synthesis and kernel integration were not started.
See `src/three_plus_three_native.py` and
`artifacts/comparator_oracle/three_plus_three/screen.json`.

## State at handoff

Updated September 10, 2026. The user wants the top rank, and the workspace now records the full experiment history, including failures. This is a research/optimization workspace, not a finished rank-1 submission.

Best (superseded, see the second continuation section below): `artifacts/full_mux.qasm`, depth **536**, CX **1020**, width **18**, generator seed **94**. The exhaustive verifier completed successfully on all 4096 clean-ancilla input basis states: maximum numerical error 1.4816382783292104e-14, ancilla error 0, accumulated discarded-amplitude bound 2.7656819215066786e-14, peak sparse support 64. Its report is `artifacts/full_mux.exhaustive.json`. SHA-256:

`93857f2dac80456feaf9c97ac464ee382eb532d8efe87e3622689103223683f0`

This is exhaustive numerical checking, not a symbolic proof. Since all basis columns are checked with one shared global phase, it also checks the action on superpositions by linearity, subject to numerical tolerance.

No challenge entry has been submitted. No current official score/rank exists for our artifact. The packaged deliverables are in `artifacts/531/`: `full_mux_531.qasm` plus its matching exhaustive report and `full_mux_531.qmod`. The QMOD is the logical oracle model; it is not expected to synthesize back to the exact pytket-optimized QASM. Do not claim rank 1.

## Strategic rethinking checkpoint (September 11, 2026)

The new unitary/state-space investigation is documented in
[`UNITARY_STATE_SPACE.md`](UNITARY_STATE_SPACE.md), with executable probes and
machine-readable reports under `artifacts/unitary_state_space/`. It tested four
structurally different explanations for a sub-183 circuit: finite-size
Nie--Zi-style phase/state compression, exact finite-group quantum branching
programs, tensor-train/MPO-to-unitary dilation, and direct ZH-diagram
simplification. None produced a new verified oracle, but the results are more
informative than another long run of the existing beams:

* the exact 12-variable truth tensor has maximum TT rank 13, so it is
  compressible but not a same-bond unitary pipeline;
* the finite-size resource audit does not support a useful constant-depth
  interpretation of the asymptotic phase-polynomial literature;
* exact QBP searches, restricted meet-in-the-middle searches, native-group
  calibration, and continuous width-2/width-4 relaxations did not reach the
  target phase;
* a direct 1,097-term ZH graph was constructed, but generic simplification
  timed out before producing a compact unitary.

This is a research closure, not an impossibility proof. The current conclusion
is that the 524/950 circuit remains the protected fallback and that the
destructive, low-multiplicative-depth/XAG, phase-history, and generic MPO
optimizer families should not receive another large run without a new theorem
or representation. Rank 1 remains unfinished; no new best is claimed.

## Three-sweep architecture checkpoint (September 11, 2026)

The dedicated `three-sweep` campaign is documented in [`THREE_SWEEP.md`](THREE_SWEEP.md),
with source under `src/three_sweep/` and artifacts under `artifacts/three_sweep/`.
It tested row-pair and phase-history reinterpretations rather than extending the
old destructive beam. The common five-bit loader verified at 64/120 depth/CX,
the 3+3 loader at 65/164, and the best transposed column-pair loader at 52/90.
The phase-rank screen rejected all 792 five-control partitions as a direct
low-depth phase bank. Exact reachable-code decoders measured 3917/3176 and
4392/3448; the best complete transposed reachable-parity oracle was **3802
depth / 2133 CX**, exhaustively verified with zero ancilla leakage.

This closes the tested direct three-sweep, 3+3, nested-shell, codebook-search,
transposed-column, and reachable-parity variants as competition paths. It is
not an impossibility proof and does not replace the protected 524/950 fallback.

## Destructive-XAG checkpoint (September 11, 2026)

The next focused experiment is the exact classifier architecture
(C^\dagger Z C), guided by the original-coordinate 97-AND XAG. The first
one-signal-per-wire allocator is now implemented and reproducible, but its
bounded topological screen requires 22 live logical registers, exceeding the
17 signal wires available after reserving the predicate wire. It runs out of
registers before node 22. This is a closure of the naive lowering only; the
planned affine-frame packing and controlled recomputation remain untested.
See `src/destructive_xag.py` and `artifacts/destructive_xag_register_pressure.json`.

The subsequent GF(2) live-rank audit gives maximum rank 34 in the original
topological order, versus 33 naive live signals. The best one-pass ready-node
schedule reduces the observed rank to about 22, but not below the 18-wire
capacity. The next falsification step is therefore topological scheduling with
dirty targets and bounded recomputation; affine packing alone is closed for
the original order. See `src/destructive_xag_rank.py` and
`artifacts/destructive_xag_affine_rank.json`.

The first bounded rematerialization screen used all 18 wires and tested
recomputation budgets through 30. It maintained exact affine rank ≤ 19 (the
constant-one vector is free) but found no
logo phase frontier; total evaluations ranged from 78 to 112 across the tested
budgets. This is only a heuristic closure of the current scheduler/model, not
an impossibility result. The trace is
`artifacts/destructive_xag_scheduler_rank19_beam50.json`; native lowering remains gated.

The corrected beam-50 rerun produced the same no-frontier result. The first
physical dirty-span prototype then kept all 18 wire functions symbolically and
implemented basis transitions (h\to h\oplus(a b)); it reached 36 guided
products with rank 19 and no phase frontier. This remains a narrow semantic
prototype because it has not yet searched arbitrary affine target directions,
repeated products, or native affine-frame synthesis.

The final repeated-product screen removed the one-use restriction and allowed
the same guided XAG product to be rematerialized whenever it left the affine
span. Beam 50 at 60, 80, 100, and 120 evaluations found no phase frontier;
each run reused nine products and reached 20 available output-cone signals.
This is the final bounded heuristic screen for this exact-XAG model, not an
impossibility proof. No QASM lowering was attempted.

## Nonlinear-spectral checkpoint (September 11, 2026)

The next proposed architecture was a shallow reversible coordinate conjugation
`U=T†D_gT`, with `g=logo∘T⁻¹`, hoping to make the diagonal phase Walsh-sparse.
Before any QASM work, `src/nonlinear_spectral.py` applied exact triangular
mutations `z_t ^= a(z)&b(z)` and measured the 4,096-point FWHT. The baseline
has 1,097 marked points and all 4,096 Walsh coefficients are nonzero.

This is forced for every reversible coordinate permutation. For every nonzero
mask, the phase-vector coefficient is twice the marked-set character sum; that
sum has 1,097 signed terms and is odd, so it cannot vanish. The constant
coefficient is `4096-2*1097=1902`. Exact screens at mutation counts 1, 2, 3, 4, 6,
and 8 therefore all retained support 4,096 and weighted support 24,576. The
reports are `artifacts/nonlinear_spectral_baseline.json` and
`artifacts/nonlinear_spectral_screen_m{1,2,3,4,6,8}.json`; the full disposition
is [`NONLINEAR_SPECTRAL.md`](NONLINEAR_SPECTRAL.md).

Close ordinary Walsh-support sparsification by reversible recoding. Do not
synthesize a QASM candidate from this screen. A future spectral attempt would
need a different representation or cost model, not more mutation depth.

## Quotient-permutation checkpoint (September 11, 2026)

The next architecture reconstructed the exact 64-by-64 matrix into 11 row
classes and 11 column classes, then treated permutations of the original x/y
data registers as free. The exact quotient and class populations are in
`artifacts/quotient_permutation_screen_200.json`; the implementation is
`src/quotient_permutation.py` and the full analysis is
[`QUOTIENT_PERMUTATION.md`](QUOTIENT_PERMUTATION.md).

The best of 200 free contiguous class layouts reduced the diagnostic proxies
to 74 reduced-OBDD nodes, 61 exact dyadic rectangles, and 551 dyadic literals.
However, compiling that exact 61-rectangle central phase with the repository's
MCZ helper measured **5877 depth / 4682 CX / 18 qubits** and passed independent
exhaustive verification. Since the central
phase alone is far above the 150-depth cutoff, no reversible `P_x`/`P_y`
search or full conjugated oracle was attempted. The quotient structure is
useful classical information, but this direct rectangle realization is closed.

## LUT-single-target checkpoint (September 11, 2026)

The next distinct representation tested conventional ABC k-LUT mappings as
reversible dirty-target gates `t ^= h(controls)`, rather than decomposing the
global logic into an XAG first. `src/lut_single_target.py` generated exact
3-, 4-, and 5-LUT BLIF networks and checked each over all 4,096 inputs. The
full node inventory and corrected local native cost databases are in
`artifacts/lut_single_target_inventory_k{3,4,5}_corrected.json`; the detailed disposition is
[`LUT_SINGLE_TARGET.md`](LUT_SINGLE_TARGET.md).

The best 3-LUT mapping has 142 LUTs, 10 levels, peak logical live pressure 35,
and a corrected optimistic dependency-weighted native path of **462 depth / 249 CX**.
The 4-LUT and 5-LUT paths are **965 / 539** and **2297 / 1334** respectively.
These local gates were verified after final U3/CX transpilation on every local
control/target basis state. The estimates still ignore target conflicts,
garbage, and inverse cost, so the 462-depth best exceeds the forward-depth
closure threshold of 120. No
global dirty-target scheduler or `C†PC` QASM was attempted. The LUT/LHRS route
is closed under this exact ABC mapping and local-gate cost model.

## Broad strategic closure (September 11, 2026)

The corrected LUT result closes more than the particular ABC mapping. Across
XAG, destructive XAG, LUT single-target, BDD/ESOP/Walsh, quotient layouts,
feature/class loaders, phase histories, and unitary/MPO/QBP/ZH probes,
conventional logic compression has not translated into native quantum depth
for this instance. The corrected best LUT forward path is 462 depth; a naive
`C†PC` form is already about 925 depth before reversible pressure, central
phase, and inverse. The previous 145/86 number is deprecated because its local
cost model used truth-table bits as ANF coefficients.

Keep this as an empirical closure, not an impossibility claim. Do not start
another Boolean representation or generic pebbling campaign without a new
operator-level construction or external evidence about the winning circuit.
The recommended next phase is reverse engineering from leaderboard metrics and
the challenge constraints. Full details are in
[`RESEARCH_CLOSURE_2026-09-11.md`](RESEARCH_CLOSURE_2026-09-11.md).

The latest `development` branch work is now also merged into `main`. It adds
the exhaustive destructive-semantic self-test plus the final signed-control,
higher-order parity, controlled-swap/Fredkin, phase-retention, local ESOP order,
and exact completion screens under `artifacts/destructive_semantic/` and
`src/`. Those experiments strengthened the earlier closure: shallow
approximate destructive classifiers and exact relative-phase candidates were
verified or exhaustively audited, but no exact sub-183 native oracle emerged.
The detailed historical report is
[`DESTRUCTIVE_SEMANTIC_SEARCH.md`](DESTRUCTIVE_SEMANTIC_SEARCH.md).

## Challenge and scoring

Source: https://www.classiq.io/challenge, visited in the user's Safari. Last observed leaderboard (historical snapshot, refresh before making current claims):

| Rank | Name | Depth | CX |
|---|---|---:|---:|
| 1 | Mateusz P. | 291 | 655 |
| 2 | Dean B. | 293 | 527 |
| 3 | Amit S. | 295 | 816 |
| 4 | Pablo C. | 303 | 645 |
| 5 | Tushar P. | 327 | 536 |

Rank 10 was depth 395; rank 14 was depth 538. Rank 1 used width 18. Do not infer a guaranteed placement from this snapshot. Observed deadline September 30, 2026; five top winners receive $2,000 each. Recheck official rules and leaderboard before submission.

The oracle must phase-mark the union of these integer-grid shapes, for x,y in 0..63:

- Square: 2 <= x <= 26 and 29 <= y <= 53.
- Bar: 26 <= x <= 49 and 39 <= y <= 43.
- Disk D1: (x-55)^2 + (y-41)^2 <= 42.
- Disk D2: (x-40)^2 + (y-19)^2 <= 72.

There are 1097 marked points out of 4096. The authoritative local predicate is `logo` in `src/search.py`. x is little-endian q[0:6], y is little-endian q[6:12]. At most six clean ancillas q[12:18] may be used. Preserve inputs and restore all ancillas. A shared global phase is acceptable. Deliverables are QMOD plus standalone QASM; depth of the exact U3/CX QASM is the main optimization target.

Original notebook: `classiq-challenge-baseline (1).ipynb`. Its saved baseline was depth 5329, CX 3502, width 18 and was verified in the notebook. It decomposes the shape into 18 disjoint rectangles. Classiq models include input Hadamards for synthesis context, but the standalone oracle removes exactly the two top-level `hadamard_transform` calls on x/y. Do not remove internal Hadamards indiscriminately.

## Critical failure and fix

Qiskit's default `qubits_initially_zero=True` let high-level synthesis treat input/dirty helper qubits as clean. An apparently excellent depth-688 pair circuit was **invalid**, with phase error 2. The same issue affected other historical low-depth MCX variants, including an apparent depth-746 candidate. The error was isolated by testing individual phase terms in `src/debug_phase.py`.

All known source transpile calls were changed to `qubits_initially_zero=False`. A rebuilt pair circuit is valid at depth 779. Old QASM files were not all rebuilt; a corrected source file does not validate its old artifact. Revalidate anything without a current matching report.

## Verified progression

| Artifact | Depth | CX | Evidence |
|---|---:|---:|---|
| `artifacts/xag_rank_True.qasm` | 1046 | 903 | Exhaustive and random-state reports |
| `artifacts/pair.qasm` | 779 | 736 | Exhaustive report; overwritten invalid 688 version |
| `artifacts/radius_mux.qasm` | 682 | 740 | Exhaustive report |
| `artifacts/full_mux.qasm` | 536 | 1020 | Exhaustive report, current best |

Verify report hashes before relying on any row. The best circuit reduces baseline depth by about 90%, but still needs a substantial reduction to beat the observed leader.

## Environment and authentication

- Workspace: `/Users/monitsharma/Downloads/classiq`.
- `.venv` Python 3.13. Use its Python, not the system interpreter.
- Installed: Qiskit 2.5.2, Qiskit Aer 0.17.2, Classiq 1.29, NumPy, SciPy, SymPy, PyEDA 0.29.
- Also installed: PySAT `python-sat` 1.9.dev15 for the native incremental SAT decomposition search.
- Newly installed and **not yet tried**: PyZX 0.10.6 and pytket 2.18.1. Installation completed successfully immediately before documentation.
- `experiments/abc/abc` is a built Berkeley ABC binary, cloned from its official repository. Build used `make -j4 ABC_USE_NO_READLINE=1`.
- PyEDA installation needed `CFLAGS=-Wno-incompatible-function-pointer-types`.
- Classiq SDK authentication was completed by the user. `CLASSIQ_TEXT_ONLY=true` was used for login. Native synthesis worked afterward. Do not expose credentials; only reauthenticate if required.
- Network package installation and Classiq synthesis previously needed approved sandbox escalation. Local optimization and verification work offline.
- No optimization process or monitor is intentionally left running at this handoff. The last verification and package-install processes both exited successfully.

## Next useful work

1. Preserve the current QASM and confirm its report hash. The independent dense verifier has now also passed on `full_mux` (5 random dense states; report `artifacts/full_mux.verification.json`).
2. The active mixed-variable LUT branch is implemented in `src/lut_decomposition.py`, `src/lut_mux_oracle.py`, and `src/search_lut_supports.py`. It exhaustively rejected all 715 four-LUT and 1,287 five-LUT combinations formed from the 13 six-input supports extracted from `experiments/logo.bench`. A separate 100-tuple random five-LUT screen found 75 UNSAT, 24 unknown, and one round-limit result; 100 additional repeated-support multisets were all UNSAT. `solve_joint_z3`, `solve_joint_z3_array`, `solve_joint_z3_bool`, and native `solve_joint_pysat` now choose arbitrary supports and LUT tables jointly with symmetry breaking; the strongest canonicalized native-SAT k=5 run completed 2,000 one-collision rounds and 2,010 pairs without a model, while a conflict-budgeted larger-batch run reached unknown at round 46. The direct all-4096-input k=4 SAT CNF (1.2M variables, 5.2M clauses) was unresolved under a 1M-conflict budget; k=5 is 1.55M variables and 6.95M clauses. The synthetic parity regression passed. This still does not cover arbitrary support tuples conclusively, so do not generalize it to all decompositions.
3. Treat the mixed-LUT branch as a completed negative direction. Do not spend another long run merely enlarging the same generic SAT formulation: the structured family was exhausted, while arbitrary-support instances became unresolved before yielding a model. This is not an impossibility proof, but it is enough to prioritize a different architecture.
4. The exported baseline has an additional structural warning: operation-touch counts are q15=403, q16=373, q17=337, q12=301, q13=261, and q14=236. Therefore the existing gate multiset has a 403-layer per-qubit serialization lower bound. Reordering or modest global cleanup cannot reach the observed ~291 leaderboard range; a meaningful result must remove or replace ancilla work.
5. Seek architectural reductions: three separate approximately 128-depth multiplexor stages dominate the current design. Simple seed search has diminishing returns. See `CURRENT_DESIGN.md` and the second-iteration conclusion in `EXPERIMENTS.md`.
6. Prototype the combined threshold-radius architecture described in `EXPERIMENTS.md`: use `V,L,T,P` instead of binary `R2,R1,R0`, express `d<=r` through the five folded-distance classes, derive `B` transiently as `y5 AND T`, and combine this with the y5 five-input lookup split. Measure the complete load/select/phase/uncompute cost; do not assume comparator removal is free.
7. A new BDD analysis found an ordinary reduced ordered BDD with about 91 nonterminal cofactor states under order `x0,x1,x5,x2,x3,x4,y5,y4,y3,y2,y0,y1`. Naive reversible OBDD realizations exceeded six ancillas, so use this only to extract a few shared cofactors or threshold predicates; do not materialize the full BDD without a workspace/reversibility plan. No QASM or checked-in BDD artifact exists yet.
8. Global PyZX/pytket rewriting remains an optional bounded diagnostic, not the main strategy. Any result must preserve qubit ordering, compile to exact U3/CX, and pass exhaustive verification after extraction/rebasing.
9. For every improvement, write a new artifact, exhaustively verify the serialized file, and update these docs with hash, depth, CX, and generator settings.
10. Keep the packaged `artifacts/531/` QASM/QMOD pair and add a clear final notebook/source explanation if submission packaging requires it. Treat the QMOD as the logical model and the verified QASM as the scored implementation.
11. Recheck official rules and leaderboard in Safari. Arrange submission only once deliverables are concrete and user-facing required fields/actions are known. No submission has happened.

## Safe reproduction

The saved seed is 94. Generate under a new name rather than overwriting the verified artifact:

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python - <<'PYCODE'
import sys
from pathlib import Path
sys.path.insert(0, 'src')
from full_mux import build
from qiskit import qasm2
q = build(94)
Path('artifacts/full_mux_rebuilt.qasm').write_text(qasm2.dumps(q))
print(q.depth(), q.count_ops())
PYCODE
OPENBLAS_NUM_THREADS=1 .venv/bin/python src/exhaustive_verify.py artifacts/full_mux_rebuilt.qasm
```

Transpiler heuristics/version changes can alter the result; the saved verified QASM is the reference, not an expectation of byte-identical rebuilding. Running `src/full_mux.py` directly searches 200 seeds and overwrites its output as improvements are found.

## Latest continuation result (September 8, 2026)

The first shell-mux implementation was completed in `src/shell_mux.py`. It
loads radius bits with a five-input y5 Shannon split, selects with Toffolis,
clears the delta bank, and reuses those wires for the existing A/B/V phase
construction. The initial CNOT-only selection was invalid and is retained as
`artifacts/shell_mux_candidate0.qasm`; it failed with phase error 2. The
corrected `artifacts/shell_mux_candidate1.qasm` passed exhaustive verification
on all 4096 inputs: depth 969, CX 1244, width 18, SHA
`6c5a35313c2f26509426fde8bbf6195fb61da742cf86576f7677fbc0c699dfa4`.
Seeds 1..7 measured 949, 965, 957, 965, 961, 969, 959, so this straightforward
split is closed as a negative direction. The baseline remains unchanged at
depth 536 / CX 1020 with SHA
`93857f2dac80456feaf9c97ac464ee382eb532d8efe87e3622689103223683f0`.
The next highest-value experiment is a genuine threshold-shell phase replacing
the binary comparator, with exact exported-QASM verification.

That experiment has now been completed as `src/threshold_shell.py`. The
verified `artifacts/threshold_shell_candidate1.qasm` uses `V,L,T,P,E`, direct
`A XOR V`/`B XOR V` loading, explicit radius-eight handling, and no binary
comparator. It passed all 4096 exhaustive inputs with zero ancilla leakage, but
scored depth 4437 / CX 3854 / width 18, SHA
`4eb6fc7fe03909714c8f135bc3512e260768c6ffdf8a8decc69282d810f3b7e6`.
The failure is architectural: each shell condition was emitted as an
independent high-control phase cube, so removing arithmetic created a much
larger unshared phase network. Do not treat direct threshold-conditioned phase
cube enumeration as viable. A future attempt would need a shared shell/UCR or
reusable folded-distance predicate before this branch is worth continuing.

## Second continuation result (September 8, 2026)

Leaderboard re-checked on the challenge page the same day: rank 1 Mateusz P.
depth 291 / CX 655, rank 2 Dean B. 293 / 527, rank 5 Tushar P. 327 / 536, rank
10 Adithya S. 395 / 514, 53 entries in total. Deadline September 30, 2026.
Still no submission from this workspace.

New verified best: `artifacts/tket_FullPeephole.qasm`, **depth 531, CX 1020,
width 18**, SHA `8f7e2617cf1435ea76cc70688544b4b0e3a8b5082d82293f98777d90d5a3fda6`,
report `artifacts/tket_FullPeephole.exhaustive.json`, all 4096 basis inputs,
maximum error 5.26e-14, ancilla error 0. It is `artifacts/full_mux.qasm` after
pytket `FullPeepholeOptimise` and a rebase to exact `u3`/`cx`; the depth-536
predecessor remains verified and unchanged. This is a 1 percent gain and closes
the global-rewriting question rather than opening a path.

`src/shell6.py` / `artifacts/shell6.qasm` is a new comparator-free architecture
built on a rank-10 bilinear decomposition plus an `x5 AND y5` conditional
reflection. It scored depth 615 / CX 1182, i.e. worse than the baseline. See
the September 8 second-continuation section of `docs/EXPERIMENTS.md` for the
full analysis, including the argument that any load / phase / unload
architecture built from 6-control uniformly controlled rotations has a hard
384-layer floor and needs about 684 CX for load plus unload alone, which already
exceeds the leader's 655 CX. The next agent should attack that primitive, not
the surrounding structure.

## Packaged depth-531 deliverables

The merged branch is now on `main`. The exact packaged QASM is
`artifacts/531/full_mux_531.qasm`, with depth **531**, **1,020 CX**, width 18,
and SHA-256
`8f7e2617cf1435ea76cc70688544b4b0e3a8b5082d82293f98777d90d5a3fda6`.
`artifacts/531/full_mux_531.exhaustive.json` was generated from that exact
path and checked all 4,096 clean-ancilla basis inputs; maximum numerical error
was `5.26e-14`, ancilla error was zero, and peak sparse support was 64.

`artifacts/531/full_mux_531.qmod` is the companion Classiq-level `qperm`
description of the same logo phase oracle. It is a synthesis model, not a
gate-for-gate serialization of the optimized QASM. No submission has been
made and no rank is claimed.

## Future path

### Disjoint geometry architecture (September 9, 2026)

The exact rewrite into pairwise-disjoint A, B', C, and D was exhaustively
checked and implemented. Standalone A and B' phase blocks measured 160/122 and
161/145 depth/CX. A disk-only block using only R0/R1/R2, with V derived as
R1 OR R2 and a free q16 phase helper, measured 385/491/18. The best complete
three-component composition was `artifacts/disjoint_geometry_708.qasm`,
708/752/18, order disk -> B' -> A, exhaustively verified with zero ancilla
leakage and SHA
`e6bf58e1782a484168da7eafbbdedd8652004e3fd18ff5c450e9365e1c9f3c3c`.

This is a verified negative result against the protected 531-depth artifact:
the two rectangle blocks serialize to roughly 321 additional layers. Direct
interval rectangles and bounded direct/hybrid radius loading were worse. Do
not continue generic ordering or seed search here; a useful follow-up would
need shared/interleaved rectangle phase loading.

That bounded follow-up was run: neither rectangle fit the existing reversible
pair compiler in a three-ancilla bank, and a two-output rectangle multiplexer
scored 384/372 alone and 767/863 with the disk block. The disjoint route is
closed unless a new shared phase primitive is developed.

A bounded GL(2,2) basis search found a better shared rectangle representation,
`A_x*(A_y XOR B_y) XOR (A_x XOR B_x)*B_y`. It reduces the rectangle block to
277/236 and the complete verified candidate to **659/727/18** at
`artifacts/disjoint_shared_rectangle_candidate.qasm`, SHA
`34b34ef926b5e7ff2748334033801a1c569f1a6009bbe31b9ebb86a8583f7007`.
This is the current best result in the disjoint branch, but it remains above
the protected 531-depth artifact.

Safe post-processing of the 659 candidate produced the current disjoint-branch
best, `artifacts/disjoint_postprocessed_649.qasm`, at **649/727/18**. It was
exhaustively verified with zero ancilla leakage and SHA
`d752c2972c16210417ef683e8ce2a5afd4501df2158829592e31dbd7911f1265`.

A five-output shared y-loader diagnostic briefly measured 525, but exhaustive
verification rejected it because its live-feature RZ phase had an
x-dependent zero-branch phase. The corrected parity-reference version reached
541/913 after a bounded loader/phase seed sweep (536/947 after bounded
cleanup), so it is not an improvement over the protected 531 artifact and no
invalid QASM was retained.

The separate-disk five-input lookup alternative was also tested and exactly
verified, but scored 482/562/18 for C XOR D (SHA
`ce807f224c92be7e46825d107c48af78c518c9a574a21b6b250851659894dd30`). It is
worse than the shared disk block and is closed.

## Joint five-output loader continuation (September 9, 2026)

The next architectural experiment is now represented by
`docs/VECTOR_LOADER_REPORT.md`. The exact y-feature vector
`(R0,R1,R2,A,B)` has 10 distinct output codewords, 36 unique ANF monomials,
and 14 shared ANF monomials. ABC's best natural-basis multi-output flow used
56 AND nodes at logic depth 8; a corrected invertible affine output-basis
screen found a 46-node network at depth 7. The y-input basis search below is
better on the depth proxy at 48/6. These figures are logic inventories, not
quantum scores.

The serialized exact minterm loader reference is
`artifacts/vector_loader_best.qasm` at **7463/3822/18**. It is intentionally a
loader-only upper baseline and is not a complete oracle. The required next
step is a reversible affine-plus-AND pebbling compiler over q12..q17, followed
by loader-only verification and then integration into the corrected 536/947
architecture. The protected complete oracle remains 531/1020/18 and is not
modified by this work.

The 531 result is a useful submission-ready baseline, but it is not close to
the historical leader at depth 291. The measurements point away from more
seed tuning or global peephole rewriting: the current architecture pays three
large six-input uniformly controlled rotation stages, and the load/unload
alone consumes roughly 684 CX. A serious improvement needs a new loading
primitive or a representation that shares/interleaves the load, phase, and
unload work.

Prioritize a compact reversible QROM/phase primitive with dirty-input
semantics, then integrate it into the existing radius/left-shape decomposition.
Every candidate must be emitted under a new filename, rebased to exact
`u3`/`cx`, and exhaustively verified with `qubits_initially_zero=False` in all
reusable-subcircuit transpilation. Keep the 531 package immutable as the
fallback submission artifact. Recheck the live leaderboard and challenge
submission fields before submitting.

The first overnight shared-XAG diagnostic was negative: composing raw
pair/XAG blocks before one global transpilation produced the verified
`artifacts/global_pair_raw.qasm` at depth 844 / 781 CX. A manual attempt to
retain a common factor across two rank terms exceeded the six-ancilla scratch
schedule. The next implementation must therefore search reversible pebbling
schedules explicitly rather than rely on global transpiler cancellation or
naive common-subtree retention.

A bounded actual-depth term-order sweep of the existing shared-XAG planner was
also negative. Its best clearing schedule was depth 1035 / 899 CX, and its
best retain-all schedule was depth 1337 / 1023 CX; both passed exhaustive
verification. Do not spend further time on ordering without changing the
underlying multi-output synthesis representation.

The first genuinely joint alternative-pair compiler is now in
`src/shared_alternative_pair.py`. On the optimized pair basis, its best local
block for terms 0 and 1 was depth 136 / 136 CX, already worse than the
independent two-term block at depth 91 / 102 CX. Replacing it in the complete
pair oracle produced verified depth 821 / 770 CX, worse than the existing
779 / 736 pair baseline. This local shared-pebbling construction is therefore
closed; any future scheduler must change the global phase representation rather
than merely retain common subtrees.

Combining the two best local groups `(0,1)` and `(6,8)` was also tested. The
full oracle scored verified depth 865 / 827 CX, so independently optimized
shared groups do not compose constructively.

A retained-x-bank schedule was also tested: it kept two complete x-side rank
factors live while streaming their y-side factors. The best feasible group
produced verified depth 892 / 783 CX, so complete-factor retention is not a
useful route under six ancillas either.

The quadrant-rank structural claim was reconstructed and verified: the four
`(x5,y5)` quadrants have ranks 1, 2, 5, and 4, for 12 terms total. The exact
selector-aware pair realization is `artifacts/quadrant_rank.qasm`, depth
1057 / 952 CX, exhaustively verified with zero ancilla leakage. This confirms
the mathematics but rejects naive quadrant compilation as an optimization path.
A specialized five-low-bit implementation with direct selector phase controls
was also corrected and verified as `artifacts/quadrant_phase.qasm`, depth
1394 / 1054 CX; it is likewise not competitive.

A native Classiq model for the whole rank-factor oracle was generated as
`artifacts/rank_formula_whole.qmod` using `experiments/rank_formula_whole.py`.
Synthesis was attempted but stopped before the API task because the local
macOS keychain returned `KeyringError: (-50, 'Unknown Error')`. No new login
was attempted and no QASM was produced from this model; retry only after the
user repairs or authorizes Classiq authentication.

PyZX extraction was also tested on the protected 531-depth QASM. Its supported
extractor produced depth 2655 / 3022 CX after U3/CX rebasing, and sparse
verification exceeded its support limit. It is not a replacement candidate.

An actual compiled-depth rank-basis search was run for 60 mutations using
`src/actual_pair_basis_search.py`. It found no improvement over the 779 / 736
pair baseline; the best accepted transient state was 783 / 724 CX and several
mutations were uncompilable. Basis search scored on the real serialized
circuit is therefore also closed as a route to the 531 baseline.

## Later continuation results (September 9, 2026)

The following additional experiments are now committed on `main` and must be
treated as measured evidence rather than open TODOs:

- `src/minmc_xag.py`: bounded Z3 XAG synthesis solved 29/30 unique scalar
  factors with independent truth-table verification. `src/minmc_rank_pair.py`
  produced only one complete three-ancilla Pareto pair, depth 139 / 215 CX.
- `src/pebble_xag.py`: a chain-shaped, pebble-friendly SAT family solved
  29/30 factors but produced only 5/10, 4/10, and 5/10 complete pairs for the
  three tested bases; partial depth sums were 771, 744, and 793.
- `src/gl10_actual_search.py`: 80 actual-cost GL(10,2) steps from each basis
  found no improvement over 779 / 736; the best alternative scores were
  795 / 754 and 803 / 751.
- `src/dirty_esop_pair.py`: direct ESOP/relative-phase MCX computation passed
  exhaustive verification but measured 2156 / 1346 CX / width 18.
- `src/phase_polynomial_aam.py`: exact Walsh GraySynth measured 8168 / 4094
  CX / width 12; all 4096 Walsh coefficients are nonzero. All section sizes
  1, 2, 3, 4, 6, and 12 gave the same result.
- `src/qrom_tree.py`: the complete verified radius-tree oracle measured 777 /
  606 CX / width 18; its lookup-only depth of 171 is not a complete score.
- Berkeley ABC AIG flows remained at 224--247 AND nodes and levels 17--22,
  exposing no compact reversible graph.

None of these candidates beat the protected `artifacts/531/full_mux_531.qasm`
(531 / 1020 / 18). The next genuinely new work must share a multi-output
phase/QROM computation while optimizing dirty-ancilla lifetime directly; do
not repeat basis search, direct ESOP, dense Walsh synthesis, generic cleanup,
or the current independent pair compiler. Native Classiq synthesis remains
blocked by the documented macOS keychain `KeyringError (-50)`; do not retry
without a real authentication/environment change.

The joint y-feature loader continuation has now also closed the naive
clean-output schedule. The natural ABC network parses exactly into 56
affine-plus-AND nodes, but none of 64 screened affine output bases allows all
five outputs to fit with five or fewer live product nodes while reserving one
clean output accumulator. This is recorded in
`artifacts/vector_feature_reversible_schedule.json`. The next justified work
is dirty-output pebbling, output-frame synthesis, or controlled recomputation;
do not interpret this bounded clean-pebble result as an impossibility proof.

The follow-up optimistic dirty-frame span probe covered only 3/5 outputs in
its best 12-toggle abstract state. It relaxed disjoint-control constraints and
therefore produced no physical candidate; see
`artifacts/vector_dirty_frame_search.json`. Any continuation must implement
the affine frame and dirty controls explicitly before treating this direction
as a score.

The local-coordinate fallback is also closed: the verified transform-only
artifact `artifacts/local_y_distance.qasm` measured 274/151/18 with three
clean scratch ancillas and passed all 64 y-input checks. Its inverse is needed
for a full oracle, making the transform pair about 548 depth before radius and
x-phase logic.

The vector-ESOP fallback is also closed. The corrected shared ANF loader uses
36 unique monomials, passes all 64 y-input checks with q17 restored, and
serializes to 2505/1453/18. The earlier 1354/840 measurement was invalid due
to reusing output wires as scratch; retain only
`artifacts/vector_esop_loader.qasm` and its metrics as the valid result.

The best new structural result is an affine y-input basis with rows
`(1,2,4,40,16,48)` and offset 16. It reduces the joint ABC inventory to
48 AND nodes at level 6. The exact shared-ESOP loader with reversible pre/post
linear mapping passes all 64 y-input checks and measures 1973/1136/18. This
is an intermediate loader improvement, not a complete-oracle result; it still
does not justify integration into the 531 architecture.

The next dirty-output test used the five feature output wires as restored dirty
ancillas for MCX synthesis. The ordinary exact version measured 1996/1130/18,
worse than the 1973/1136 clean-output loader. Relative-phase compute/fanout/
uncompute reduced the loader-only score to **1560/874/18** in
`artifacts/vector_input_basis_dirty_rp_loader.qasm`; all 64 y inputs were
independently statevector-verified with exact outputs, restored y and q17, and
one shared global phase. This is not a complete logo oracle and has not been
integrated into the protected 531 artifact.

The subsequent direct-output schedule toggles feature accumulators in place for
each shared cube and uses the other output wires as restored dirty ancillas.
It measures **1478/823/18** in
`artifacts/vector_input_basis_direct_target_loader.qasm`, improving the
1560/874 relative-phase q17 loader. All 64 y inputs were statevector-verified
for exact output bits, restored y and q17. It has four internal relative-phase
classes and is therefore only a loader/inverse primitive, not a standalone
oracle; it has not been integrated into the protected 531 circuit.
The serialized loader followed by its exact inverse reduced to identity under
U3/CX transpilation (depth 0 / CX 0), confirming cancellation of the internal
relative phases.

The required complete integration was also run in `src/vector_loader_oracle.py`:
the direct five-output loader plus derived `V` was composed with the original
phase/correction logic. Eight seeds produced a best **3243/1965/18** candidate
at `artifacts/vector_loader_oracle_candidate.qasm`; it passed exhaustive
verification but is decisively worse. The loader-only improvement therefore
does not transfer to the complete oracle and this integration route is closed.

The persistent output-frame scheduler is the strongest vector result so far.
It produces an exact loader at **871/553/18** and the complete integration at
**2032/1425/18** (seed 1), with exhaustive 4096-input verification and zero
ancilla leakage. This is substantially better than the direct-target
integration but remains above 531; the next work must reduce the remaining
phase/correction and loader serialization rather than repeat the same frame
screen.

The independent `V = R1 OR R2` control experiment replaced the six-output UCR
with a five-output UCR plus an exact reversible OR. Its best verified score was
545/945/18 over 32 seeds; pytket lowering reached 540/945, still worse than
the protected 531/1020/18. The matching optimized artifact is
`artifacts/full_mux_derive_v_tket.qasm`, SHA
`4baad4c76a20db8e92ea7e2f2f68a0d8d9041e570d33275903bf38e3c228e39b`.
The sixth-lookup removal alone is closed.

A targeted direct-`B(y)` replacement was also exact but negative: the bar was
computed reversibly into q16 while the remaining five features used the UCR
loader. The candidate measured **634 depth / 968 CX / 18 qubits**, passed all
4096 basis inputs with zero ancilla leakage, and is retained at
`artifacts/hybrid_b_mux.qasm` with SHA
`a9be69b2cdf4172a547982108e94a26d28520a0cccb88130e20dd9d341877331`.
Single-feature substitution does not remove the loader bottleneck.

The follow-up independent y/x routing search tested 4,096 seed pairs and
reached a verified **537/921/18** after pytket. Artifact:
`artifacts/full_mux_derive_v_independent_best_tket.qasm`, SHA
`5b1878c951599e594ef404d219c46f4a1fdd412ee50a516d6c16ff53e5f44146`.
This is a strong CX near-miss but still does not improve depth 531.

Relative-phase Toffolis for the temporary V derivation were also safe under
full verification. A 1,024-pair screen reached **535/918/18** after pytket;
artifact `artifacts/full_mux_derive_v_rp_or_best_tket.qasm`, SHA
`a7ef23f038c2f4f1b6309899025283b32656d17fcd142f21618c9aeb013769f2`. This is
four layers above 531, so it is a near-miss rather than a replacement.

## Feature assignment improvement (September 9, 2026)

An exhaustive permutation search over the six physical feature wires in the
full-mux skeleton found a verified new best:

`artifacts/530/full_mux_feature_permuted_530.qasm`

It measures **530 depth / 1,020 CX / 18 qubits**, improving the protected 531
depth by one layer without changing CX count. The assignment is
`R0->q12, R1->q15, R2->q14, A->q16, B->q17, V->q13`. The phase-cube target and
V control were remapped explicitly; hard-coded-wire variants with lower raw
scores failed phase verification and were discarded.

The exact QASM SHA-256 is
`7f9676b2d372d9ca5eb31889bf9f3af1d6fc4a678bd9b782f6e67ef707938156`.
`artifacts/530/full_mux_feature_permuted_530.exhaustive.json` records all 4096
basis inputs, maximum error `1.52e-14`, and zero ancilla leakage. The dense
random-state report also passed. Reproduction is in
`src/feature_ancilla_permutation.py`.

The protected 531/QMOD package remains unchanged. No Classiq upload was made
by this experiment.

The follow-up independent-routing screen tested 2,048 combinations over the
eight strongest assignments, with separate y-loader, x-phase, and transpiler
seeds. It did not improve 530; its best was 530/1022. A six-order radius
comparator schedule screen also found no improvement over 530/1020. These
are bounded negative results, not reasons to reopen generic seed searches.

The five-output `V = R1 OR R2` architecture was also remapped over all 120
feature assignments using its best known y/x routing seeds. Its best verified
result was **539/918/18**, so assignment remapping does not rescue that
branch. The next work should attack the UCR/multiplexer primitive itself.

## Verified 529-depth affine feature encoding (September 10, 2026)

An invertible GF(2) encoding of all six y features was tested in the complete
oracle, with exact decode before the existing phase logic and reverse decode
before loader uncompute. Matrix rows `(1,6,2,8,16,32)` produced the first
verified improvement after the 530-depth feature-wire search:

```text
depth 529 / CX 1036 / width 18
SHA 9d07529b678b046085fa5c0a32b4774e04cb6ba3650e779e4200609e133bc477
```

The QASM is `artifacts/529/full_mux_feature_linear_529.qasm`, with matching
exhaustive and dense reports and a logical QMOD companion. Exhaustive
verification covered all 4096 inputs with zero ancilla leakage; the dense
verification covered five arbitrary full-support states. This supersedes the
530-depth circuit as the local best, but does not approach rank 1. The source
is `src/feature_linear_encoding.py`; the next optimization should search
structured affine encodings and, more importantly, seek a primitive that
removes the three UCR load/phase/unload stages.

An independent-control-order screen then tested 101 complete candidates with
arbitrary six-bit permutations for each y-loader and x-phase output, rather
than the cyclic orders used by `multiplexer()`. The winning feature assignment
again measured **530/1020/18**, and none of the 100 arbitrary-order candidates
improved it. This rules out control-order scheduling as the main remaining
lever; a future improvement must replace or share the UCR primitive itself.

## Final fallback checks (September 9, 2026)

The prescribed local-coordinate fallback was revisited with relative-phase
controlled arithmetic. The 64-input mapping remained exact, but the serialized
transform measured **302/181/18**, worse than the exact 274/151/18 transform.
Because the transform must be computed and uncomputed around the phase, this
does not justify integration.

The documented 109-node BDD was also evaluated with dirty input workspace. The
result measured **3,949,563 depth / 2,581,968 CX / 18 qubits**, so direct BDD
materialization is closed. The current justified research target remains a new
shared phase/QROM primitive; no existing candidate is promoted over the
verified 530/531 package.

## Structured two-shear continuation (September 10, 2026)

The affine feature search was extended from single shears to all 870
nonsingular two-shear compositions and 24,240 nonsingular three-shear
compositions at the winning physical assignment. Three successive one-shear
extensions around that winner, with matrix rows `(9,23,21,8,17,32)`, produced
the current verified best:

```text
depth 527 / CX 950 / width 18
SHA f83b8695497cca51d13b29e90d6eff184d5cb6def7619511caca79f794192309
```

`artifacts/528/full_mux_feature_linear_528.qasm` passed exhaustive verification
on all 4096 inputs and five dense full-support checks. The matching logical
QMOD and both reports are packaged under `artifacts/528/`. This is still a
local improvement only; rank 1 requires replacing the UCR-based primitive.

## Verified 524-depth pytket post-processing result (September 10, 2026)

Pytket `FullPeepholeOptimise` and `CliffordSimp` were applied to the verified
527/950 QASM. Both produced **524 depth / 950 CX / 18 qubits** after exact
U3/CX lowering; a 100-seed final transpiler screen found no further change.

The accepted artifact is
`artifacts/524/full_mux_feature_linear_tket_524.qasm` with SHA
`7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147`.
It passed all 4096-input exhaustive checks and five dense full-support checks,
with matching reports and a logical QMOD under `artifacts/524/`. The verifier
reported numerical errors of `1.11e-13` exhaustive and `3.98e-15` dense, with
ancilla leakage below `2e-14`. This supersedes the raw 527-depth serialization.
Repeated pytket pass compositions and a bounded native `rz/sx/x/cx` intermediate
basis screen did not improve 524/950; the latter reached 525/950 at best. The
accepted 524 artifact remains unchanged.

All 720 feature assignments were also screened by raw score, and pytket was
run on the 30 strongest. Every raw 527/950 tie post-processed to 524/950, so
physical assignment is not the remaining post-processing lever.

A direct 12-variable Walsh/GraySynth diagnostic used all 4,096 Walsh terms and
serialized to 8,168 depth / 4,094 CX / 12 qubits before verification. Its
phase convention failed the logo verifier, so it is not an accepted artifact;
the cost alone closes dense full-Walsh synthesis as a replacement for the
three synchronized lookup stages. Additional pytket pass compositions and
ordering variants all reproduced 524/950 and found no post-processing gain.

A further screen compiled 100 random nonsingular GL(6,2) output frames through
the complete affine-feature oracle. The best raw result was 538/1014; the two
raw 538-depth winners post-processed to 533/1006 and 527/1028. Neither beats
the accepted 524/950 artifact. Results are in
`artifacts/random_affine_screen.json` and
`artifacts/random_affine_screen_post.json`; arbitrary dense output frames are
not the next justified lever.

The sparse-Walsh UCR experiment is also closed. It was exact over all 4096
inputs and reduced CX to 949, but its variable-length paths serialized the
outputs to **563 depth / 949 CX / 18 qubits**. Retain it only as a negative
primitive result; the dense synchronized UCR remains superior at 524/950.

An early-lifetime schedule was also tested: after the left-shape phase it
uncomputed `A` and `B` with an interleaved two-output inverse UCR before the
radius comparator, then cleared `R0,R1,R2,V` afterward. The exact candidate is
**653/1010/18**, with all 4096 inputs verified and zero ancilla leakage, at
`artifacts/early_uncompute_ab.qasm` (SHA
`b179123b316a18964d911fb894674656c36c811ded6151d4a9975b0324584a25`). This
does not improve the protected 524/950 result.

The left-shape x phase was also rewritten as eight direct ESOP-controlled
phase cubes, removing the three-target x-UCR. The exact candidate measured
**795/1049/18**, passed all 4096 inputs with zero ancilla leakage, and is at
`artifacts/direct_left_phase.qasm` (SHA
`e84248ff0ece3b8b6f7a83d9ea962b1ed4b1654afd88adbe58c9bfee9c80a70e`). This
phase-only replacement is worse than the synchronized x-UCR.

A complete y-input coordinate-frame screen then wrapped the affine-feature
oracle in 40 random nonsingular GL(6,2) maps plus the known low-cost map. The
known map reached **530/978/18** and the best random map reached 536/1020;
none improved 524/950. The results are recorded in
`artifacts/complete_input_basis_screen.json`; input-coordinate changes alone
are closed as the next lever.

All 64 affine offsets for the winning six-feature matrix were also compiled;
raw results were 527/950 or 529/950, and every tied offset lowered to exactly
524/950/18 under pytket. The results are in
`artifacts/complete_affine_offset_screen.json` and
`artifacts/complete_affine_offset_post.json`. The complete affine frame is now
bounded-closed; further progress requires a new reversible primitive.

A new shared Shannon/Davio vector compiler was implemented for the five-output
loader. It passed a sparse exact check over all 64 y inputs, but serialized to
**2385/1336/18**, far worse than the 128-layer UCR loader. The source is
`src/shared_vector_shannon.py`; the QASM, metrics, and 64-input check are under
`artifacts/shared_vector_shannon_loader*`. This shared cofactor representation
is not a viable complete-oracle primitive.

The relative-phase action/reset variant reduced the same loader to
**1646/933/18** while preserving exact output bits and q17 cleanup on all 64
y inputs. It is stored at `artifacts/shared_vector_shannon_rp_loader.qasm`
with its metrics/check files, but remains far above the UCR loader depth and
was not integrated.

## Comparator-free threshold phase pilot (September 10, 2026)

`src/threshold_phase_ucr.py` found a valid classical identity for the folded
disk region: on the exact disk guard, each relevant folded-x row is an affine
parity of the loaded features `V,L,T,P,Q,B`, where `L=[r>=4]`, `T=[r>=6]`,
`P=r&1`, `Q=T&P`, and `B=y5&T`. The exact reversible implementation used
MCZ/ESOP phase cubes and exact dirty compute/phase/uncompute for `T` and `Q`.

It passed all 4096 basis inputs with zero ancilla leakage, but scored **1265
depth / 1460 CX / 18 qubits**. The artifact is
`artifacts/threshold_phase_ucr_candidate.qasm`, SHA
`5bfb917963e8a237bae9d4db7c3eb8b4000ff0307f0395299a86f425d2dd23b3`.
This is a verified negative result against the protected
`artifacts/524/full_mux_feature_linear_tket_524.qasm` at 524/950/18. The
direct threshold-phase replacement is closed; only a new shared
phase-gadget/QROM compiler would justify revisiting it.

An exact branch-corrected UCR variant was also measured. It uses synchronized
UCR feature phases and a six-qubit diagonal to cancel each UCR's x-dependent
zero branch, with exact compute/phase/uncompute for the two nonlinear feature
terms. The serialized artifact is
`artifacts/threshold_phase_ucr_ucr_corrected_candidate.qasm`, SHA
`4a6deced9376fd428c177174b695e5c8473f6acf2953f8e8138c4d6879a45845`, at
**969/1338/18**. Exhaustive verification covered all 4096 inputs with zero
ancilla leakage. It is better than the 1265/1460 exact-MCZ pilot but still
well above the protected 524/950 result, so this representation is closed.

A six-output threshold encoding was then tested: `[V,L,T,P,A,B]`, with only
`Q=T&P` computed transiently into dirty `V`. It removes the binary-radius
comparator while retaining the existing left-shape logic. The candidate
`artifacts/threshold_feature_oracle_candidate.qasm` is exhaustively verified
on all 4096 inputs at **781/1318/18**, SHA
`0ccd69c5bd92478aa9df35d27546f0839e3e7894242b1545609fd1da5a5adea4`, with
zero ancilla leakage. It improves the 969-depth pilot but does not improve
the protected 524/950 circuit, so this encoding is also closed.

## Development branch joint-rank feasibility diagnostic (September 9, 2026)

The proposed three-term rank batch was tested against the exact XAG pebble
planner. No pair or triple from `rank_terms`, `pair_terms`, or
`rank_mc_pareto_terms` was jointly feasible with three live ancillas on each
side. At a four-ancilla limit, many pairs were feasible, but no triples were
feasible. The reproducible scan is `src/joint_rank_feasibility.py`, with output
in `artifacts/joint_rank_feasibility_development.json`.

A bounded elementary rank-basis mutation screen tested 40 mutated bases and
480 sampled pairs under the three-ancilla limit, finding no feasible pair. Its
diagnostic output is `artifacts/joint_rank_basis_search_development.json`.
This is not an impossibility proof because it uses the existing formula/XAG
representation and a bounded planner state budget. It does show that the
original rank basis cannot directly support the planned 3+3 prototype; future
work needs a new multi-output or phase/state synthesis primitive.

The follow-up synchronized three-term rank batch is exact but not complete:
`src/rank_batch_ucr.py` and `artifacts/rank_batch_ucr_012_development.qasm`
implement terms `(0,1,2)` from `rank_terms` at **257/535/18**, with an
exhaustive product-phase report and zero ancilla leakage.  Since ten terms need
multiple serialized batches, this does not improve the protected 524-depth
oracle.  A separate exact phase-state retention probe for one product term is
`src/direct_product_retention.py`; its checked term-0 artifact is
`artifacts/direct_product_retention_term0_exact_development.qasm` at
**222/225/18**.  Neither artifact is a complete logo oracle or submission
candidate.

For rank term 0, a retained-product pilot kept the nonlinear x-root live while
streaming eight y-side phase edges. The first 162-depth RCCX version was
invalid because relative phases did not cancel and pooled temporaries were not
forced to an exact retained set; it remains only as
`artifacts/direct_product_retention_term0_development.qasm`.

The corrected exact-CCX version is
`artifacts/direct_product_retention_term0_exact_v2_development.qasm`, at
**508/407/18**. It passed `src/verify_product_term.py` on all 4096 inputs for
the standalone target `(-1)^(a_0(x)b_0(y))`, with maximum error `5.73e-15`
and zero ancilla leakage. SHA-256:
`4847944094e71f419e4574ee689cdcb535f39a014c0729b760b7b185815faca5`.
This is a correctness baseline, not a complete-logo improvement. Exact
cleanup eliminated the apparent 162-depth advantage, so a useful future
phase/state construction must prove relative-phase cancellation locally.

`src/rank_batch_ucr.py` then implemented a genuine 3+3 rank batch for terms
`(0,1,2)`: synchronized x/y UCR loads, three parallel CZ couplings, and exact
inverse cleanup. The new partial-oracle artifact
`artifacts/rank_batch_ucr_012_development.qasm` measures **257/535/18** and
passed `src/verify_product_term.py` on all 4096 inputs for the XOR of the three
rank products, with maximum error `1.27e-14` and ancilla leakage
`2.18e-15`. SHA-256:
`cdb69043c2f87599b203881d40377332e2066ad4d99a49d5c8fdb43a7a395410`.
A seed screen over seeds 0--7 kept depth fixed at 257, with CX counts from
511 to 555. Thus the UCR batch validates the parallel architecture but does
not by itself meet the full-logo target; reducing the ~128-layer bank loads or
sharing them across rank batches remains necessary.

An ESOP alternative in `src/rank_batch_esop_dirty.py` used the other five
ancillas as dirty scratch for each output. It compiled to **672/433/18** but
failed the three-term exhaustive phase check with error 2, demonstrating that
the retained-output relative phases do not cancel across this multi-output
sequence. The artifact `artifacts/rank_batch_esop_dirty_012_development.qasm`
is a negative diagnostic only.

A five-factor streamed-bank variant in `src/rank_batch_streamed.py` loaded
five x-factors once with UCR and streamed each y-factor through the remaining
ancilla using the retained x-bank as dirty scratch. It measured **753/781/18**
but failed the five-term exhaustive product check with phase error 2. The
current relative-phase predicate loader therefore cannot safely stream a
factor across a live bank; exact phase-safe loading remains necessary.

An exact no-ancilla MCX ESOP implementation in
`src/rank_batch_exact_esop.py` was also tested for terms `(0,1,2)`. It passed
the standalone three-term product verifier on all 4096 inputs, with maximum
error `1.21e-14` and zero ancilla leakage, but serialized to **1431/823/18**.
The artifact is `artifacts/rank_batch_exact_esop_012_development.qasm`, SHA
`ec84910237b1ef9fae762ab21af832bd09db9947375ffa19ccd743d2b55fb49b`.
This closes exact per-cube MCX loading as a depth improvement over the
257-depth UCR batch.

Global pytket `FullPeepholeOptimise` and `CliffordSimp` rewrites were also
applied to the verified UCR batch. Both preserved the three-term semantics
but returned exactly **257/535/18**; their serialized outputs share SHA
`332524c727f4c0dd5491cd6524656e3d09f798a1f242955f83d712246e15bed6`.
Compiler-only post-processing is therefore closed for this batch.

## Development branch direct bilinear phase synthesis (September 9, 2026)

The diagonal phase-cube compiler was applied directly to rank-factor ESOP
products, without materializing either factor. Individual rank terms measured
**66/52**, **199/119**, and **251/162** for terms 0, 1, and 2 respectively;
each passed exhaustive product-term verification.

The complete rank-10 expansion reduced to 69 diagonal cubes. A 20-seed search
found a best complete candidate at **1725/1235/18**. The candidate
`artifacts/rank_phase_only_full_development.qasm` passed the complete logo
verifier on all 4096 inputs with zero ancilla leakage. SHA-256:
`f4ed4e259eb477fcfd72bf721937963c00270624924ab6bc14e05766b639d882`.
Unshared direct bilinear phase expansion is therefore closed; future work
must share phase cubes globally or use a different multi-output representation.

The exact-MCZ serialization of the same 69-cube phase-only construction was
also checked at **1734/1235/18**, SHA
`af295b60cd6f48c8eebde5fd05d6539556bbdb40f14c547b13beeda727759f32`; it
passed all 4096 inputs but is slightly deeper than 1725/1235 and is closed.

The same global cube-sharing recursion was rerun with `mcz.best_mcz` replacing
the older phase-cube primitive. The best of eight seeds was **1734/1235/18**
and passed complete exhaustive verification with zero ancilla leakage. SHA:
`af295b60cd6f48c8eebde5fd05d6539556bbdb40f14c547b13beeda727759f32`.
This is slightly worse than the 1725-depth phase-only result; MCZ helper
selection is not the missing improvement.

An elementary GF(2) basis search scored complete serialized direct phase-only
circuits after each mutation. The best of 100 steps kept depth at **1725** but
reduced CX count from 1235 to **1225**. The candidate
`artifacts/phase_rank_basis_best_development.qasm` passed the complete logo
verifier on all 4096 inputs with zero ancilla leakage; SHA-256:
`f6d52201ba8f066b388d2a25d94a1348b6b14625f024263de53c3fb4a06c5542`.
Search data is in `artifacts/phase_rank_basis_search_development.json`.
Basis choice changes cube sharing and CX count but not the depth regime; this
is a verified near-miss, not a replacement for the 524-depth oracle.

An additional 100-step annealing variant was exhaustively checked at
**1770/1243/18**, SHA
`a75ec65fa04e2948171cf5e92e64b415cdcd1269a5ec07735196afad5e8beb7b`; it is
deeper than 1725/1225 and is closed.

## Development branch grouped phase-sharing pilot (September 9, 2026)

The 69 direct bilinear phase cubes contain 23 distinct y-side ESOP cubes.
`src/shared_y_phase_grouped.py` computes one y-cube into q17, synthesizes all
associated x-side phase cubes with a shared q17 control, then uncomputes q17.
This reduces the naive grouped-y implementation from 4100 depth to a verified
**2242/1624/18**. The complete candidate
`artifacts/shared_y_phase_grouped_development.qasm` passed all 4096 logo inputs
with zero ancilla leakage; SHA-256:
`d18d1530e7615e64fab0bdd1a2a13e32e685a005966fd6b6f1c4f31d78eb4f29`.
It remains above both the protected 524-depth oracle and the 1725-depth global
phase-only candidate, so local y-group sharing is insufficient.

## Phase/state-duality applicability review (September 9, 2026)

The referenced Amy--Ross phase/state-duality paper studies both relative-phase
circuits and measurement-assisted temporary logical-AND constructions. The
measurement-assisted portion cannot be directly used for this challenge: the
deliverable is a standalone unitary `u3`/`cx` QASM oracle with arbitrary inputs
preserved and all ancillas restored. Only the unitary relative-phase part is
applicable, and the repository's retained-product and multi-output experiments
show that relative phases must be proven to cancel across every intervening
operation. No paper construction is imported as a candidate without an
explicit unitary realization and exhaustive verification.

A separately generated retained-product term-0 variant was subsequently
verified as a standalone product phase: `artifacts/direct_product_retention_term0_development.qasm`
measures **162/173/18**, SHA
`636e9f66f5d6a4af275a9335919275f6b1c21d4e7a10ef658733f1a453649f4d`, with
maximum error `2.93e-15` and zero ancilla leakage over all 4096 inputs. This
is a valid component diagnostic, not a complete logo candidate; the exact
reproducible retention builder's term-0 artifact remains 508/407.

## Cofactor-bank continuation (September 10, 2026)

The first implementation of the proposed cofactor direction is
`src/cofactor_rank_bank.py`. It adapts the existing Shannon/Davio tree emitter
to a three-output rank bank for terms `(0,1,2)`, with three CZ phase couplings
and inverse cleanup. The exact clean-workspace control is
`artifacts/cofactor_rank_bank_012_clean_development.qasm` at **1330/767/18**;
its SHA is `f1f619b1077985bd5b4ad05835ddb564ff533142a3eb5378f58a4eb1f65f0e6b`.
The standalone product verifier checked all 4096 inputs with maximum error
`1.20e-14` and zero ancilla leakage.

The cross-bank dirty-workspace variant appeared to reach **309/205/18**, but
failed the exact three-term phase check with error 2. Replacing relative-phase
Toffolis by exact CCX still failed at **501/359/18**. These are invalid
diagnostics: the recursive cofactor program does not preserve its branch/frame
invariant when the live output bank is borrowed as scratch. The clean control
is far above the existing 257-depth UCR batch, so no rank-basis search is
justified yet. The next meaningful compiler work must make the dirty or
conditionally-clean invariant explicit rather than treating any available
ancilla as interchangeable scratch.

The phase/state-duality follow-up is `src/cofactor_product_phase.py`. It
computes the three x factors with the cofactor bank, applies the y factors
directly as phase ESOPs controlled by the live x outputs, and then uncomputes
the x bank. The exact standalone three-term product candidate is
`artifacts/cofactor_product_phase_012_development.qasm`, **484/290/18**, SHA
`66e27f13d5b28455b4d721e80eff95712328d4a96e8d12fff65f22df4dfa4512`. It
passed all 4096 product-phase checks with maximum error `1.10e-14` and zero
ancilla leakage. This is phase-safe but slower than the 257/535 UCR batch;
direct y ESOP phase cubes remain the bottleneck. A shared phase-gadget
compiler is required before extending this formulation beyond three terms.

The exact two-live-pair vector continuation was also tested in
`src/exact_vector_stream.py`. It kept two x/y factor pairs live in q12..q15,
used q16,q17 as clean transition scratch, and streamed five consecutive
two-term groups. The complete verified scores were **2948/1702** for
`pair_terms`, **2774/1601** for `rank_terms`, and **2716/1576** for
`rank_mc_pareto_terms`, all at width 18 with zero ancilla leakage. This exact
vector stream is a negative result; the current path does not justify a
relative-phase extension without changing the transition representation.

The exact one-live-pair stream requested in the next research plan was then
implemented in `src/exact_stream.py`. It uses phase-free MCX transitions between
factor states, scores all zero/term edges in native `u3`/`cx`, and solves the
term order with Held--Karp. The best complete verified result is the
`pair_terms` candidate `artifacts/exact_stream_pair_terms_development.qasm` at
**1227/1361/18**, SHA
`f44158faeac79cd6623b893d78fa00a505471f96ca90040be81229f1ce2cd3d1`.
The corresponding `rank_terms` and `rank_mc_pareto_terms` candidates score
1267/1322 and 1303/1455. All three passed exhaustive 4096-input verification
with zero ancilla leakage; the best pair candidate also passed five dense
full-support states. Exact one-pair streaming is therefore closed by the
400-depth cutoff. The historical stream's full reverse cleanup was not the
only issue: exact native transition costs and repeated factor deltas dominate.

The complete integration was then tested in `src/cofactor_full_oracle.py`,
using groups `(0,1,2)`, `(3,4,5)`, `(6,7,8)`, and `(9,)`. The exact standalone
logo candidate is `artifacts/cofactor_full_rank_phase_development.qasm` at
**1685/1026/18**, SHA
`ed6d6168559f968e29905468f2ef59ecc1bc30c740a2850c26c43916baaa1422`. It
passed exhaustive verification over all 4096 logo inputs with maximum error
`2.60e-14` and zero ancilla leakage; five dense full-support checks also
passed with maximum error `4.89e-16`. This is the full-problem score, and it
is decisively worse than the protected 524/950 oracle. The cofactor
temporary-product route is closed in this form.

The final bounded cofactor check used explicit exact HP24 no-ancilla MCX
lowering in `src/cofactor_rank_bank_hp24.py`. Its verified three-term product
candidate `artifacts/cofactor_rank_bank_012_hp24_development.qasm` measures
**1611/1895/18**, SHA
`ed81bf69e55db8fc72bfa168c9a5b7aeecd2ac4f9049425fbfc79053109f654a`.
All 4096 product inputs passed with zero ancilla leakage, but the result is
worse than both the ordinary cofactor control and the 257/535 UCR batch.
Explicit HP24 lowering does not rescue the cofactor architecture.

## Closed architecture branches (September 10, 2026)

Stateful factor streaming, multi-live-factor streaming, and Shannon/cofactor
materialization are now closed as primary routes. Exact one-pair streaming
bottomed out at 1227/1361/18; exact two-pair streaming at 2716/1576/18; and
the cofactor/HP24 experiments remained far above the protected result or failed
exact phase checks. Do not reopen these with incremental seed or helper changes.
The protected fallback remains
`artifacts/524/full_mux_feature_linear_tket_524.qasm` at **524/950/18**, with
matching exhaustive and dense verification.

## Conditionally-clean cofactor pilot (September 10, 2026)

`src/conditionally_clean_cofactor.py` regenerated the proposed selector
profiles from the authoritative logo predicate. The four-bit split
`(x5,y3,y4,y5)` has nine nonzero branches with ranks
`4,2,1,3,2,4,2,4,1`; the complete screen is in
`artifacts/conditionally_clean_screen.json`.

The hardest rank-4 branch, assignment 3 (`x5=1,y3=1,y4=0,y5=0`), was compiled
both conservatively and with selector wires borrowed as dirty ancillas. The
safe reference scored **946/518/18**. The conditionally-clean candidate
`artifacts/conditionally_clean_branch_3_borrowed.qasm` scored **904/522/18**,
SHA `70c32ab29c4fd7d9af61fcf21fb2d59ef0bece7fec3fe2c9193b80a379785a0c`, and
passed a branch-specific exhaustive check with zero ancilla leakage. The
candidate marks only that cofactor; its report must not be mistaken for a
complete-logo verification.

The workspace mechanism is therefore valid, but independent ESOP phase-cube
lowering is far too deep. Do not integrate all branches yet. The next and
only justified follow-up is to factor the residual truth table before quantum
lowering; if that remains above the local cutoff, close this direction too.

The branch-3 profile has 11 cubes, 67 literals, 12 containment relationships,
and a most-common literal pair appearing 10 times. A classical scan of all
220 three-bit, 495 four-bit, and 792 five-bit selector sets is recorded in
`artifacts/conditionally_clean_selector_scan.json`. The best four-bit split by
raw total ESOP cubes is `(x5,y2,y4,y5)` at 68 cubes across 11 branches,
slightly ahead of the tested `(x5,y3,y4,y5)` split at 70 cubes across 9
branches. This scan only ranks representations structurally; it does not
replace exact native U3/CX scoring.

The first targeted factorization used the signed factor
`(x4=0) AND (y2=1)` and an exact bounded six-variable XAG for its residual.
The branch-3 factored candidate scored **713/445/18**, SHA
`611c3f8a51595fbca49102b6f6c4728ea6c96b7966834e417308669b4a7fef1c`, and
passed branch-specific exhaustive verification with zero ancilla leakage. This
improves on 904/522, but remains above the local viability gate. Do not build
all branches yet; the next checkpoint is another factor/XAG representation or
another rank-4 branch, not full selector traversal.

The factored pilot was ablated into `P*G` and `R`: **323/249** and **459/248**
respectively, both exact under their extracted predicates. A bounded complete
8-variable XAG search found no solution through two AND nodes and timed out
(`unknown`) at three and four nodes with 5-second budgets. The search artifact
is `artifacts/branch3_xag8_search.json`; this is a bounded diagnostic, not a
proof that no larger XAG exists. The next work should target a native decoder
or multi-level lowering; do not integrate all cofactor branches yet.

## Closed direction: conditional-clean cofactor/XAG (September 10, 2026)

Close this implementation line for the competition objective. The mechanism
itself is correct, but the exact ablations are **323/249** for `PG`, **459/248**
for `R`, and **713/445** for the complete branch. Neither component is a small
nuisance term relative to the sub-190 target, and the bounded whole-branch XAG
search returned no small candidate. Keep the verified artifacts as evidence,
but do not spend further optimization time on this representation. The
protected fallback remains `artifacts/524/full_mux_feature_linear_tket_524.qasm`
at **524/950/18**.

## Closed direction: finite-size Lupanov/rich-width branch (September 10, 2026)

The bounded `src/lupanov_branch.py` pilot instantiated the smallest directly
valid rich-width parameterization for the eight-variable branch (`q=1,p=7`)
with ten workspace wires. After compute--Z--uncompute, the exact candidate
scored **20432/11260/18**, SHA
`f91ad1511021a2f045be32df47b45a7ba127fa5eef414fb4e72b1e6bcbbed80a`, and
passed all 256 residual-input checks. This is far above the stop threshold;
close the finite-size Lupanov implementation for this challenge. The result is
a finite-constant diagnostic, not a lower-bound proof against the paper's
asymptotic construction.
## Depth-window resynthesis pilot (September 9, 2026)

The protected 524 QASM was profiled without modifying it. The exact input SHA
is `7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147`; the
profile reports **524 depth / 950 CX / 18 qubits**, 580 zero-slack gates, and
U3-family counts of 213 diagonal, 610 general, plus 950 CX gates. The largest
ASAP-layer CNOT+diagonal region spans layers 127--257 but touches 14 wires, so
it is not a small exact-unitary peephole. The profile and candidate ranking are
in `artifacts/524/full_mux_feature_linear_tket_524.window_profile.json` and
were generated by `src/window_profile.py`.

The first strict exact-unitary pilot tested the tractable late pockets. The
contiguous 3-wire windows at layers 483--487 and 498--504 reproduced at the
same local depth/CX and left the full circuit at **524/950**. The larger
apparent 473--482 and 473--487 pockets were interleaved with unrelated gates
in serialized order and were rejected rather than unsafely spliced. The full
measurement is `artifacts/524/full_mux_feature_linear_tket_524.strict_window_pilot.json`;
the pilot is implemented in `src/strict_window_pilot.py`.

This closes only the first ordinary exact-window peephole test, not care-set
resynthesis. The next justified step is to select dependency-aligned boundaries
where the six clean ancillas are zero/classical and resynthesize on reachable
states; preserve the 524 artifact as the protected baseline.
## DAG and semantic-window preparation (September 9, 2026)

The bounded dependency-DAG inventory is in
`artifacts/524/dag_window_inventory.json`, generated by
`src/dag_window_resynthesis.py`. It confirms the protected SHA and 524/950
score, recovers 19 small causal candidates within the 3--6-wire budget, and
finds late candidates whose selected gates are serialized-interleaved (for
example layers 471--483 and 492--504) without an internal dependency crossing.
This supports DAG extraction as a real distinction from textual contiguity,
but no replacement has been synthesized or scored yet.

The semantic care-state mappings for 64 legal inputs are in
`artifacts/524/semantic_window_mappings.json`; selected blocks are `(R0,R1)`,
`(R1,R2)`, `(A,B)`, and `(A,B,V)`. Strict Walsh reference costs are recorded in
`artifacts/524/semantic_pair_results.json`: the pair/triple references measure
128/128, 109/110, 128/128, and 128/172 depth/CX respectively. BQSKit 1.2.1 was
installed in the project virtual environment and imported successfully, but a
bounded 8-qubit StateSystem QSearch smoke test (64 states, max layer 2) hit its
60-second stop bound. Therefore no numerical semantic candidate is being
claimed; the next run should use a deliberately small ansatz or specialized
state-system objective.

## Subspace-quotiented shared-XAG search (September 9, 2026)

The high-degree ANF screen has been implemented in
`src/semantic_subspace_xag.py`. For each target, monomials of degree at least
five are extracted and ranked over GF(2); the selected pairs have rank 2 and
the `(A,B,V)` triple has rank 3, giving analytic shared-AND lower bounds of 4
and 5 respectively. This upgrades the earlier timeout-through-3 result, but
only for the stated affine-AND XAG model.

The same script searches canonical GF(2) spans rather than affine-expression
syntax. At the 4/5-AND minima it reached the second node layer and hit a
5,000-state cap for all tested groups. The report is
`artifacts/semantic_discrete/subspace_xag_results.json`; all search statuses
are bounded `state_limit`, not impossibility proofs. No native RCCX schedule
or full-oracle candidate exists yet.

## Discrete shared-XAG screen (September 9, 2026)

`src/multioutput_minmc.py` implements the proposed 64-bit truth-signature
shared-XAG model: each AND node has affine inputs over the six y bits and all
earlier nodes, while every requested feature is an affine output of the shared
node set. The shallow screen is recorded in
`artifacts/semantic_discrete/joint_xag_results.json`. For `(R0,R1)`, `(R1,R2)`,
`(A,B)`, and `(A,B,V)`, no model was returned through three shared AND nodes
with 1-second-per-bound limits. These are solver `unknown_or_above_bound`
results, not lower bounds; no reversible candidate was produced and no full
oracle score changed. The next escalation, if justified, is a heuristic
bit-parallel beam search rather than a blind increase in Z3 timeout.
## Exact-completion candidate search (September 9, 2026)

`src/semantic_xag_completion.py` implements provenance-tracked Gaussian
completion for target quotient directions, while enumerating first and second
AND extensions one span at a time. The first bounded `(R1,R2)` run examined
all 651 first-node extensions and 424,445 second-node extensions in 10 seconds,
but reached zero late completion tests before the time bound. Its report is
`artifacts/semantic_discrete/r1_r2_completion.json`. This is a frontier
management result, not evidence against a four-AND witness; the next change
must target-direct the second-node enumeration before invoking completion.

## Completion-gate correction (September 9, 2026)

The earlier completion report had a real quotient bug: a rank-2 quotient has
three nonzero directions, not two, so `len(directions) != 2` rejected every
ordinary pair state before completion. `src/semantic_xag_completion.py` now
separates quotient basis from nonzero directions, preserves each actual
`f & g` product and its affine correction, and exposes bounded smoke limits.
The regression tested 321 second-node states and reached 9 direction tests;
the corrected 1,000-state sample reached 21 direction tests with no witness.
Its report is `artifacts/semantic_discrete/r1_r2_completion_fixed.json`.
This supersedes the interpretation of the earlier zero-test report. The
sample is not a lower bound and no native candidate exists yet.

## Suspended direction: semantic shared-XAG synthesis (September 9, 2026)

Suspend this line for the competition objective. The sequence from semantic
care-state mappings through BQSKit, shared-XAG lower bounds, subspace search,
and corrected target completion produced no native circuit candidate and no
improvement over the protected **524 depth / 950 CX** oracle. This does not
prove that four-AND `(R1,R2)` or five-AND triple constructions are impossible;
it means further solver engineering is not currently justified. Preserve the
lower-bound reports and completion code as research evidence, but do not spend
additional optimization time on this branch unless a new lowering architecture
appears.
## EPFL oracle-synthesis stack check (September 9, 2026)

The proposed mature-flow experiment was checked before any circuit work. The
project `.venv` has no RevKit, Mockturtle, Caterpillar, or Tweedledum module.
PyPI has no `revkit` distribution. The available PyPI `caterpillar` name is an
unrelated text-retrieval package and was removed. Tweedledum 1.1.1 is source
only here and fails its Python 3.13 build during metadata generation due to an
invalid project configuration. Therefore no EPFL oracle synthesis or score
was run; do not confuse the unrelated package installation attempt with the
reversible Caterpillar tool. A compatible Python/toolchain environment would
be required before this becomes an actionable bounded campaign.

## EPFL compatibility attempt (September 10, 2026)

One disposable Python 3.12.9 environment was created at
`/private/tmp/epfl.uDo5uH`; the project `.venv` was not changed. Current
Tweedledum source built successfully there as version 1.2.0. RevKit `develop`
cloned successfully but its unmodified build failed first on undeclared
`pybind11`, then again after installing `pybind11` and `setuptools`; no RevKit
module was installed. Mockturtle and Caterpillar remained C++ source trees,
and no executable RevKit/Caterpillar oracle flow was available. Under the
one-attempt stop rule, close this environment line as blocked; do not patch
upstream build systems or continue platform-specific troubleshooting.
## Classiq-native full-function attempt (September 10, 2026)

The fresh direct-arithmetic geometry model is preserved as
`artifacts/classiq_direct_geometry.qmod`, generated by
`src/classiq_direct_geometry.py`. The model gives Classiq the four exact shape
inequalities and phase-marks their union; an initial draft that phase-marked
the four shapes independently was corrected because the square/bar boundary
overlap would otherwise cancel.

The first native synthesis request failed immediately with an expired Classiq
token and the API reported that the arithmetic model requires at least 39
qubits despite `max_width=18`. Per the stop rule, authentication was not
debugged and no QASM or score was produced. This is a blocked/invalid direct
model attempt, not a negative result against all Classiq-native synthesis.

## Classiq-native campaign closure (September 10, 2026)

The refreshed credentials allowed API requests. The direct arithmetic union
model was rejected by the Classiq API at **82 minimum qubits** versus the
18-qubit constraint, so it cannot be a competition candidate. The natural
row-class and whole low-rank formula requests created/updated their QMOD
inputs, but neither returned a new exported QASM within the bounded wait;
their pre-existing QASM files were not treated as fresh results. Thus this
campaign produced no score-bearing circuit. Per the agreed stopping rule, do
not continue Classiq authentication or synthesis debugging. The protected
verified baseline remains **524 depth / 950 CX / 18 qubits**.
## Final strategic status (September 10, 2026)

The six-feature UCR architecture is formally closed, not merely the current
best. The protected 524 QASM places feature `A` on q16; that wire touches 405
gates, including 206 CXs, and carries 394 of the 580 critical gates. Its
activity spans the y-load, x-phase, and inverse y-load, explaining why local
compiler changes stay near 524 rather than approaching 200. The published
parallel-UCR pattern is already exploited in the implementation.

All explored methods and their dispositions are consolidated in
`docs/EXPERIMENTS.md`. The protected verified 524/950 artifact and original
notebook are retained; no experimental artifact is promoted without complete
verification. In particular, do not reopen Tweedledum PKRM/optimum
phase-ESOP, GUOQ/QUESO, Synthetiq, BQSKit local windows, further XAG search,
Classiq-native synthesis, or coordinate coding. These are closed outcomes,
not pending installation or tuning tasks.
## Coordinate-recoding diagnostic (September 10, 2026)

The proposed QFT-based conditional low-5-bit recentering was implemented in
`src/qft_recenter.py`. The exact transform was checked on all 64 y inputs and
compiled standalone to **81 depth / 58 CX / 18 qubits** with
`qubits_initially_zero=False`. Because this exceeds the agreed `<50-depth`
go/no-go threshold, close the coordinate-recoding/staircase architecture
without attempting the larger 11x11 in-place class transform. The artifact and
metrics are `artifacts/qft_recenter.qasm` and
`artifacts/qft_recenter_metrics.json`.
## Hard closure of internal architecture invention (September 10, 2026)

The QFT recenter result is a hard closure, not an invitation to seek a better
implementation of the same idea. Its exact 81-depth forward transform would
require an approximately 162-depth forward/inverse pair before any logo phase
logic, leaving no credible path to sub-200 depth. Together with the completed
UCR, row-class, rank/cofactor, XAG/shared-XAG, ESOP, conditional-clean,
Lupanov, state-system, exact/semantic-window, retained-predicate,
coordinate-transform, QFT, Classiq-native, and external reversible-synthesis
experiments, the evidence rules out incremental compiler improvements as the
explanation for the missing ~300 layers.

Stop active internal architecture invention. The verified 524/950 artifact is
the submission fallback; remaining work should be limited to explicit
submission and external investigation of the structural technique used by
competitive solutions.

## Cross-branch strategic closure after the 21-hour run (September 11, 2026)

A review of `main`, `development`, `multiplicative-depth`, and
`another-one`, including the latest destructive-search commits, changes the
diagnosis. The remaining gap is not best explained by insufficient search
time. The explored branches have optimized the wrong circuit classes for the
competition objective. The current leaderboard depth of **183** is retained
here as the working challenge target reported during this review; it is not a
new local score or a claim about the leader's construction.

| Branch | Circuit class tested | Evidence | Conclusion |
|---|---|---|---|
| `main` | Six-feature UCR load/phase/unload | Verified **524 / 950 / 18**; the architecture is heavily serialized and q16 carries a large critical workload | The architecture is closed; compiler tuning cannot plausibly remove the roughly 300-layer gap |
| `development` | Destructive semantic classifiers, high-order corrections, dirty/clean completion, and controlled swaps | Shallow approximate classifiers exist, but exact completion expands to thousands of layers; the semantic implementation was independently self-tested over all 4096 inputs | Destructive semantics are valid, but classifier Hamming/affine residual is not a useful leading objective for an exact shallow oracle |
| `multiplicative-depth` | Exact low-MD XAGs | MD=4 reaches 5096 ANDs; a smaller exact XAG reaches 81 ANDs at MD=6, while the best native realization remains about **1023 / 899** | Multiplicative depth does not translate into native quantum depth; affine transport, live values, and recomputation dominate |
| `another-one` | Historical phase signals and phase-history constructions | Shallow histories reach rank 29 around depth 88 and rank 26 around depth 106, but the target never enters the span; the exact shared-XAG proposal is **1345 / 1027** | Removing final classical output is conceptually useful, but the explored RCCX/RC3X trajectory family does not generate the target cheaply |

The destructive branch is therefore a mapped negative landscape rather than an
unfinished beam campaign. Forward points improved the best affine residual
from approximately 331 at depth 79, through 315 at depth 90 and 279 at depth
108, to 197 at depth 146, but that residual still measures truth-table points
outside the available affine span. Exact completions remained in the
many-thousands-of-layers regime. Exhaustive local screens of RCCX neighbors,
higher-degree monomials, persistent-CX transformations, affine and signed
controls, and controlled swaps found no escape from this regime.

The apparent combination with `another-one` was also checked directly. The
depth-79 no-uncompute trajectory reached historical rank 27 and the depth-90
v2 trajectory reached rank 28, but neither contained the logo phase in its
span. The depth-92 signed/positive trajectory likewise did not contain the
target. Thus no hidden sub-200 construction was found by combining the
existing shallow destructive histories with phase-history synthesis.

### Disposition

Close the destructive beam campaign, multiplicative-depth search, XAG
rewrites, and current phase-history trajectory family. Do not spend more time
on larger versions of these searches or on compiler tuning of the protected
UCR architecture. The verified **524 / 950 / 18** artifact remains the
fallback and is unchanged. A future attempt is justified only if it introduces
a genuinely different structural idea, such as external structural
intelligence or reverse engineering of the circuit class used by the leading
solution. Rank 1 has not been achieved, and no local result should be
represented as such.

## MPO-native branch status (September 11, 2026)

The new `mpo-native-synthesis` branch is the first materially different
structural direction after the cross-branch closure. It contains an exact
TT/MPO representation of the logo phase, a full process-overlap objective,
an exact non-adjacent gate contraction, and topology generators for all-to-all
matchings. The target's interleaved TT order has maximum exact rank 13, and
the target sign tensor reconstructs to numerical precision.

The adjacent RieADAM brick-wall family plateaued near process fidelity
`0.3020024`; its best abstract 4-layer checkpoint compiles to depth 25 / CX 64
but is only approximate and is not promoted. The non-adjacent contraction
matches dense evaluation to about `4.0e-21`. Differentiating through dynamic
MPO QR/SVD splitting was not viable in the installed JAX version, so the
bounded one-layer direct-overlap test reached `0.1917240554` after 200 steps.
This is diagnostic only. The next real task is a fixed-coordinate,
multi-layer, non-chain tensor-network optimizer followed by exact QASM
promotion and exhaustive verification.

The gatewise Procrustes optimizer is now implemented in
`src/mpo_gate_sweep.py`. It contracts exact local environments using cached
tensor-network paths and performs polar/SVD updates. The bounded results are
round-robin 2-layer fidelity 0.355433, round-robin 4-layer fidelity 0.358981,
round-robin 6-layer fidelity 0.369852, TT 6-layer fidelity 0.301523, and x-y
4-layer fidelity 0.282325. The round-robin 4- and 6-layer checkpoints compile
to depth 17 / 48 CX and 25 / 72 CX respectively, but remain large-error
approximations. The six-layer run took about 818 seconds for five sweeps;
eight-layer round-robin contractions became impractical, so no unsupported result
was recorded. Fixed-topology extension
is not currently a credible route; the next experiment should be adaptive
matching selection or the explicitly deferred four-ancilla bus ansatz.

The first four-ancilla bus ansatz is now also measured. With explicit clean
ancilla boundaries and gatewise Procrustes updates, two bus interactions per
data qubit reached 0.259720 and four reached 0.265659 after 15 sweeps. This
is below the no-ancilla matching result and the schedule family is closed;
only a materially different multi-pass/isometric bus construction would
justify more work.

The stronger sequential-memory test in `src/mpo_sequential_unitary.py` gives
each data step an arbitrary 32x32 unitary on the four-qubit memory plus data.
Twenty Haar restarts converged to 0.266116–0.266156; memory dimensions 32 and
64 did not improve it. The simple single-pass sequential architecture is
closed. A fixed-topology Riemannian probe optimizer also failed to beat exact
gate sweeps. The executable MPO invariant suite is now six tests, all passing.

The promotion wrapper `src/promote_mpo_candidate.py` now checks serialized
`u3/cx` basis and width, records the QASM SHA, and invokes the repository
exhaustive verifier. It rejected the depth-17 round-robin QASM with max error
about 2.0, so no MPO artifact is verified or promoted.

An analytic 15-parameter SU(4) Adam ladder was also tested. Exact fidelity
rose from 0.5690 at 24 layers to 0.6434 at 32 and 0.6616 at 40, but the
40-layer native compile was depth 241 / 720 CX. The trend is too slow for the
183 target, so fixed round-robin SU(4) depth expansion is closed. No artifact
from this ladder is a candidate.

An analytic four-ancilla bus Adam control was also checked with 64 fixed trace
probes. Its 48-SU(4)-gate schedule reached only 0.373421 after 150 steps,
below the no-ancilla ladder; the bus schedule is closed.
