# Continuation handoff

## State at handoff

Updated September 10, 2026. The user wants the top rank, and the workspace now records the full experiment history, including failures. This is a research/optimization workspace, not a finished rank-1 submission.

Best (superseded, see the second continuation section below): `artifacts/full_mux.qasm`, depth **536**, CX **1020**, width **18**, generator seed **94**. The exhaustive verifier completed successfully on all 4096 clean-ancilla input basis states: maximum numerical error 1.4816382783292104e-14, ancilla error 0, accumulated discarded-amplitude bound 2.7656819215066786e-14, peak sparse support 64. Its report is `artifacts/full_mux.exhaustive.json`. SHA-256:

`93857f2dac80456feaf9c97ac464ee382eb532d8efe87e3622689103223683f0`

This is exhaustive numerical checking, not a symbolic proof. Since all basis columns are checked with one shared global phase, it also checks the action on superpositions by linearity, subject to numerical tolerance.

No challenge entry has been submitted. No current official score/rank exists for our artifact. The packaged deliverables are in `artifacts/531/`: `full_mux_531.qasm` plus its matching exhaustive report and `full_mux_531.qmod`. The QMOD is the logical oracle model; it is not expected to synthesize back to the exact pytket-optimized QASM. Do not claim rank 1.

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

## Destructive ESOP borrowed-ancilla continuation (September 10, 2026)

The exact destructive v6 classifier was lowered with Qiskit's
`synth_mcx_2_dirty_kg24`, borrowing and restoring two non-control wires per
ESOP cube. The exact forward classifier is **9,011/7,687** depth/CX; the
complete serialized oracle is **17,575/15,000**. The verified QASM is
`artifacts/destructive_semantic/high_order_affine_exact_esop_dirty2_oracle.qasm`
with SHA256
`2f1bf81bbe17baed2842b16aa1912382814cb806aedb6f778fe2d7631051eccb`.
Exhaustive verification covered all 4,096 basis inputs with max error
`2.979403618689416e-13`, zero ancilla leakage, and discarded-amplitude bound
`5.726332944000072e-12`. This is a correctness artifact, not a competitive
candidate or leaderboard claim; the protected 524/950 fallback is unchanged.
