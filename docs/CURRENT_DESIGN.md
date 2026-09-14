# Protected baseline: parallel lookup and shared disk comparison

## Latest bounded follow-up: nonlinear phases and local windows

See `docs/POST190_NONLINEAR_AND_WINDOWS.md`. Best remains **190/857/18**.
A 673-case nonlinear/LP screen reduced phase support to 51 but the best full
alternative was 200/859, exhaustively verified. 240 local window trials did not
improve 190. Corrected x-tag and inverse-Walsh/phase-unit errors in the older
reachable-lift experiment; corrected eight-start search retained 63 terms.
Old runs using those erroneous helpers do not establish architectural limits.
Four focused tests pass; all runs finished and protected QASM hash unchanged.


Current verified best is **190 / 857 / 18**, `artifacts/190/`, SHA
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`.
The latest work investigates structurally different direct Boolean oracles;
its 139-layer template is unsolved and is not a submission artifact. See
[POST190_NEW_ARCHITECTURES.md](POST190_NEW_ARCHITECTURES.md). Earlier entries
below are historical checkpoints.

Latest: **193 / 853 / 18**, `artifacts/193_cx853/`, a CX tie-breaker gain only.
Depth is unchanged. Exact-file exhaustive verification, five dense checks and
matching QMOD pass. See [POST193_CX_REFINEMENT.md](POST193_CX_REFINEMENT.md).

Current best, September 14: **193 / 857 / 18**, exact-file exhaustive verification,
five dense checks, matching QMOD and deterministic replay in `artifacts/193/`.
The new kernel is phase plus an ancilla permutation; inverse encoders are
rewired accordingly. See [POST193_RESEARCH.md](POST193_RESEARCH.md) and
`src/build_two_stage_193.py`. Sub-140 and rank one remain unfinished.

The following 196 entries are historical checkpoints.

Latest nonlinear-coordinate experiment: correct complete circuit **204 / 891 / 18**,
exhaustively verified, so best remains **196 / 858 / 18**. See
[NONLINEAR_LOADER_PROBE.md](NONLINEAR_LOADER_PROBE.md). No rank-one result is claimed.

New arithmetic component result: verified four-bit comparator **25 depth**, or **36 enabled**, using two clean helpers. Full logo best remains 196. Read [ARITHMETIC_MIDDLE_PROBE.md](ARITHMETIC_MIDDLE_PROBE.md) before interpreting the latest frame-model claims.

Current milestone: **sub-140 first**, then further reduction toward rank one. See [SUB140_SEARCH.md](SUB140_SEARCH.md) for the new Boolean, quadratic-feature, and conditional-loading experiments. Best verified full circuit remains 196 / 858 / 18.

Status, September 13: leader observed at 142, target sub-100, local verified
best **196 / 858 / 18**. The claimed universal floor in the latest side analysis
is invalid; read [POST196_FLOOR_AUDIT.md](POST196_FLOOR_AUDIT.md). No lower-depth
oracle has been produced by this audit.

Latest objective: **sub-100 and rank one**. The 196-depth baseline has been independently reproduced and exhaustively rechecked. The leader observed in Safari is 142 / 557 / 18. Read [POST196_RESEARCH.md](POST196_RESEARCH.md) for the output-layout correctness fix and new bounded searches. No improved complete circuit or rank-one result is claimed.

Current best, September 13: **196 depth / 858 CX / 18 qubits**, `artifacts/196/`, exact-file exhaustive verification, five dense checks, matching literal QMOD, deterministic rebuild via `src/build_two_stage_196.py`. SHA `63333fade2e7e38c9a4edf333888c26bdac234c04e955fd6a624c0ea6e714c30`. Structure is unchanged from the 218 package; the kernel schedule is now a beam search (`src/post218_beam_phase.py`). The loaders are 77 layers each and dominate the cost. The floor arguments in `docs/POST218_RESEARCH.md` apply to restricted lookup constructions; they are not general optimality proofs (see `POST196_RESEARCH.md`). Sub-180 and rank one remain unresolved.

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

**Earlier best was 258/1188/18**, using the distributed phase implementation
of the two-level-comparison identity. Its complete current design is
[DISTRIBUTED_LOOKUP_258.md](DISTRIBUTED_LOOKUP_258.md), and the verified package
with a matching QMOD is `artifacts/258/`. The remainder of this file describes
the historical protected 524 fallback. The earlier architecture closures below
are superseded where the new implementation demonstrates otherwise.

Earlier audit (historical): [DEPTH_GAP_ANALYSIS_2026-09-12.md](DEPTH_GAP_ANALYSIS_2026-09-12.md)
recorded the 456/1140 level circuit as the then-current local depth best; the 524 design
below remains a preserved fallback. Pure rescheduling of the 456 artifact has
a 389-depth per-wire floor. Alternative default-code UCG components remain
127 depth each. No new best or rank-one solution was produced.

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


For the complete method inventory, research references, experiment status, and
cross-branch handoff, see [`METHOD_INDEX.md`](METHOD_INDEX.md) and the detailed
chronology in [`EXPERIMENTS.md`](EXPERIMENTS.md).

Status note (September 11, 2026): this architecture is a verified fallback,
not an active optimization target. The cross-branch review in
`docs/HANDOFF.md` also closes the current destructive, low-multiplicative-depth,
XAG-rewrite, and phase-history families. Reaching the reported 183-depth
leaderboard target requires a materially different structural circuit class;
compiler tuning or a larger run of those searches is not considered a useful
next step.

The subsequent structural rethink is recorded in
[`UNITARY_STATE_SPACE.md`](UNITARY_STATE_SPACE.md). Exact tensor-rank/TT
analysis, finite-size phase-state auditing, quantum-branching-program probes,
same-bond unitary feasibility checks, and direct ZH construction all produced
diagnostic evidence but no replacement circuit. This file therefore describes
the fallback only; new work should not quietly turn its feature-load/
phase/unload architecture back into the default search objective.

The September 11 `three-sweep` campaign tested the main alternative row/column
code architecture. Its loaders were individually correct, but exact phase and
decoder constructions were thousands of layers deep; the best was 3802/2133
and is not a replacement. See [`THREE_SWEEP.md`](THREE_SWEEP.md) for the full
measurements. A genuinely new representation is required before another large
optimization run.

 Implementation: `src/full_mux.py` / `src/feature_linear_encoding.py`, importing
the radius, phase-cube, and pair helpers. The protected post-processed artifact
is `artifacts/524/full_mux_feature_linear_tket_524.qasm` at **524 depth / 950
CX / 18 qubits**, with matching exhaustive verification. This architecture is
now closed for competition optimization; this document explains the fallback.

## Register layout

| Qubits | Meaning |
|---|---|
| 0..5 | x, little endian |
| 6..11 | y, little endian |
| 12 | R0 in the protected affine feature assignment |
| 13 | V: radius(y) > 0 |
| 14 | R2 in the protected affine feature assignment |
| 15 | R1 in the protected affine feature assignment |
| 16 | A: y in 29..53 (square rows) |
| 17 | B: y in 39..43 (bar rows) |

All six ancillas start and end at zero.

## Radius table

D2 rows: y=11,27 -> r=2; y=12,26 -> 4; y=13,14,24,25 -> 6; y=15..23 -> 7. The actual radius is 8 on y=17..21; the two extra points x=32 and x=48 on those rows are handled by a separate final phase pair.

D1 rows: y=35,47 -> r=2; y=36,46 -> 4; y=37,38,44,45 -> 5; y=39..43 -> 6. Other rows have r=0.

The two disk bands are separated by y's top bit. This permits a shared coordinate reflection and comparison.

## Parallel multiplexors

`multiplexer` computes Walsh-Hadamard coefficients of a Boolean table scaled by pi, emits Gray-code-ordered RY (lookup) or RZ (phase) rotations and connecting CNOTs. Each output uses a different cyclic shift of a shuffled control order. Consequently, CNOTs for different outputs can run in parallel on distinct control/target pairs. The seed selects these orders; it does not change the intended function.

The first stage loads R0,R1,R2,A,B,V into six ancillas in parallel. Each 6-control multiplexor has 64 rotation/CNOT positions, giving an approximately 128-depth stage before compiler cancellations. Lookup phases are acceptable because the same full lookup is inverted after the central diagonal action and restored comparator.

## Left-shape phase identity

Partition x into S=2..26, Bx=27..48, and O=everything else. The square/bar overlap is removed from Bx. First replace A by A XOR V and B by B XOR V, using two CNOTs. Apply three parallel controlled RZ multiplexors:

- RZ(pi*S(x)) on A XOR V.
- RZ(pi*Bx(x)) on B XOR V.
- RZ(pi*O(x)) on V.

Exactly one of the three x indicators is one. Using RZ(pi)|t> = -i*(-1)^t|t>, the total phase is -i times (-1) to the power of (left-shape indicator XOR V). A Z on V removes the extra V phase. Restore A and B with inverse CNOTs. The remaining factor -i is one shared global phase.

This replaces separately synthesized square and bar circuits with one approximately 128-depth parallel phase stage. It is essential that S, Bx, O partition all x values.

## Shared disk comparison

1. Reflect the lower four x bits conditionally on y5 by four CNOTs from q11. D1's low-four-bit center 7 maps to 8; D2's center is already 8.
2. Fold the lower three bits depending on bit x3. This produces a folded distance with an offset on the negative side; retain x3 as the initial carry to correct that offset.
3. Invert the folded three bits, and run a three-step Cuccaro-style majority chain using relative-phase Toffolis. Each step applies CX(radius_i, x_i), CX(radius_i, carry), RCCX(carry, x_i, radius_i). The last radius bit holds the comparison carry.
4. Phase-mark only when V, x5, (x4 == y5), and the comparison carry are all one. The equality is formed temporarily by CX(y5,x4), X(x4). `phase_cube` implements the four-factor MCZ with available dirty helpers and no assumed clean workspace.
5. Undo equality, comparator, and folding. Invert the entire six-output lookup to clear ancillas.
6. Apply the independent correction pair for x in {32,48}, y in 17..21.

The left shapes and the split disk representation avoid unwanted XOR overlap. The full Boolean specification is checked independently by `logo` during verification.

## Optimization opportunities and hazards

### Formal closure of this architecture

The six-feature UCR load/phase/unload design is no longer an active
optimization direction. Profiling the protected QASM finds q16 (feature `A`)
touching **405 gates**, including **206 CX gates**, and carrying **394 of 580
critical gates**. It is serialized through the y-feature multiplexer, x-side
phase logic, and inverse y-feature multiplexer. The parallel-UCR opportunity is
already exploited; further compiler, permutation, or local cleanup cannot
remove the architecture's dominant load/unload cost. A materially different
abstraction would be required to approach sub-200 depth.

The lookup, left-phase lookup, and inverse lookup each cost roughly 128 depth. The comparator, guarded phase, folding, and final edge correction account for the rest. This explains why seed tuning alone may not reach below 291.

The exported QASM makes this bottleneck more concrete. Counting all operations
that touch each clean ancilla gives q15=403, q16=373, q17=337, q12=301,
q13=261, and q14=236. Since operations on the same qubit serialize, the
current gate multiset has a 403-layer per-qubit lower bound. This is not a
lower bound on every possible circuit for the predicate: a new architecture may
remove those operations. It is, however, strong evidence that modest gate
reordering, seed changes, or local compiler cleanup cannot bridge the gap to a
leaderboard depth around 291.

Global circuit rewriting may cancel gates across stage boundaries, but can also increase depth or produce dense intermediate states that are expensive to verify. Compare final U3/CX depth, not just T count, abstract gate count, or a library's native gate depth.

The strategic consequence is to prioritize architectural changes that reduce or
share the three lookup/phase/uncompute stages. The row/column class decoder and
the second-iteration mixed-support LUT decomposition are not primary directions:
the former was empirically too deep, and the latter exhausted its structured
support families while unrestricted SAT searches became unresolved before a
quantum candidate existed. Global PyZX/pytket rewriting remains worth a bounded
diagnostic, but it should not be expected to transform the current gate multiset
from depth 536 to the leader range by reordering alone.

A separate classical analysis found an ordinary reduced ordered BDD with about
91 nonterminal cofactor states under variable order
`x0,x1,x5,x2,x3,x4,y5,y4,y3,y2,y0,y1`. This suggests that some predicates may be
shared across the three lookup stages. However, naive reversible OBDD
realizations exceeded the six clean ancillas, so the actionable interpretation
is to mine the BDD for a small number of reusable cofactors rather than to
implement the full diagram. This is currently an analysis lead, not a verified
quantum construction.

The next concrete architectural hypothesis comes from the radius lookup. `y5`
separates the D2 and D1 nonzero disk bands, so each radius bit can be written as
`h0(y0..y4) XOR (y5 AND Delta_h(y0..y4))`. This replaces one six-control UCR
table by two five-input tables plus a y5-controlled selection. For the three
radius bits, the six tables could be loaded in parallel, potentially reducing
the UCR portion from about 128 to about 64 layers.

This is not yet a drop-in replacement: the six tables consume all six clean
ancillas as two three-bit banks, while the existing design uses those same wires
for the six simultaneous features `R0,R1,R2,A,B,V`. The Delta bank must be
uncomputed before reuse, or the radius and left-shape feature groups must be
sequenced. The first implementation should therefore measure an isolated
radius load/select/unload circuit before changing the verified baseline.

A stronger version should also replace the binary radius representation. The
actual radius set is `{0,2,4,5,6,7}`, so use threshold/parity flags
`V=[r>0]`, `L=[r>=4]`, `T=[r>=6]`, and `P=[r odd]`. After folding, the five
possible distance classes use these flags as follows: `d<=2` uses V,
`d in {3,4}` uses L, `d=5` uses `T OR P`, `d=6` uses T, and `d=7` uses
`T AND P`. This may eliminate the Cuccaro-style comparator rather than merely
shortening its input lookup.

The bar lookup is also redundant in this representation: direct evaluation
confirms `B = y5 AND T` for every y. A candidate can therefore form B
transiently and avoid treating `R0,R1,R2,A,B,V` as six independent stored
outputs. The phase implementation must still be synthesized and exhaustively
verified; the threshold identities alone do not establish a depth improvement.

The first complete comparator-free implementation was tested in
`src/threshold_shell.py`. It was correct but scored depth 4437 / CX 3854 because
it emitted each threshold-conditioned distance shell as an independent
high-control phase cube. This demonstrates that deleting arithmetic is not
enough: the shell phase must itself be shared or implemented as a compact UCR
network. The verified artifact is recorded in `docs/EXPERIMENTS.md`; the
depth-536 baseline remains the trusted reference.

The first split-loader prototype is a verified negative result. `src/shell_mux.py`
and `artifacts/shell_mux_candidate1.qasm` implement the five-input Shannon
radius load with Toffoli selection and delta cleanup. The exact candidate is
depth 969, CX 1244, width 18, SHA
`6c5a35313c2f26509426fde8bbf6195fb61da742cf86576f7677fbc0c699dfa4`.
The trusted `full_mux` baseline remains unchanged.

Changing relative-phase components or helpers can invalidate an otherwise correct classical computation. Keep arbitrary input semantics in every compiler call, restore all temporary values before inverse lookup, and verify each exact exported circuit. No symbolic optimization should bypass numerical verification.

## MPO-native synthesis status (September 11, 2026)

The active experimental branch is `mpo-native-synthesis`. It represents the
logo as an exact diagonal TT/MPO in the interleaved order with maximum rank
13, and its arbitrary-pair contraction has been checked against dense
evaluation. The adjacent brick-wall optimizer plateaued near process
fidelity 0.302 and is not a route to a verified candidate. A bounded
non-chain autodiff test reached 0.191724 after 200 steps using the exact
one-layer operator overlap; this is diagnostic only. No candidate has been
promoted, and the verified 524/950 fallback remains unchanged.

The gatewise MPO Procrustes sweep is the current no-ancilla optimizer. Its
best bounded round-robin result is process fidelity 0.369852 at six SU(4)
layers, compiling to depth 25 / 72 CX but remaining approximate. TT and x-y
families plateaued lower, and eight-layer round-robin environment contractions
became impractical. Do not interpret these shallow native metrics as a
verified oracle or as a new repository best; the exact promotion pipeline is
still required.

The analytic Adam ladder reached exact fidelity 0.6616 at 40 round-robin
SU(4) layers, but native compilation was already depth 241 / 720 CX. This
confirms that fixed matching depth expansion is not competitive; the result is
diagnostic and unpromoted.

The analytic four-ancilla bus Adam control reached only estimated fidelity
0.373421 with 64 trace probes, below the no-ancilla ladder. This bus schedule
is closed and no ancilla-assisted circuit has been promoted.

The four-ancilla bus diagnostic used explicit clean-subspace boundaries and
reached only 0.265659 process fidelity after 15 sweeps with 48 SU(4) gates.
It is below the best no-ancilla result and is closed for this schedule
family; no bus circuit has been promoted or verified.

The stronger sequential-memory block ansatz and Riemannian control were also
negative: 20 Haar restarts of arbitrary 32x32 memory/data blocks converged to
0.266116–0.266156, and the batched trace-gradient control did not beat the
exact gatewise sweep. The six-test MPO invariant suite passes; all numerical
results remain approximate and unpromoted.
