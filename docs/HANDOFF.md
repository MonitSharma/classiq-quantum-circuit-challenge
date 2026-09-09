# Continuation handoff

## State at handoff

Updated September 8, 2026. The user wants the top rank, and most recently requested Markdown files containing everything tried, including failures, so a different chat/agent can continue. This is a research/optimization workspace, not a finished rank-1 submission.

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
