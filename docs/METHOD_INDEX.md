# Complete method and research index

Updated September 11, 2026. This is the map of the Classiq logo-oracle
research program. The chronological measurements and failure notes remain in
[`EXPERIMENTS.md`](EXPERIMENTS.md); this file is the compact index for a new
agent or collaborator.

## Scope and status vocabulary

The objective is an exact standalone `u3`/`cx` QASM implementation of

```text
U|x,y,0^6> = (-1)^logo(x,y)|x,y,0^6>
```

with arbitrary input values on q[0:12], clean and restored q[12:18], at most
18 qubits, and one allowed shared global phase. Every reusable-subcircuit
transpile must use `qubits_initially_zero=False`. A method is **verified** only
when the serialized QASM itself passes `src/exhaustive_verify.py` and the
report SHA matches that exact file. An abstract optimizer score, component
score, stochastic fidelity, or stale report is not a verified oracle.

The protected local fallback is:

```text
artifacts/524/full_mux_feature_linear_tket_524.qasm
depth 524 / CX 950 / width 18
SHA-256 7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147
```

No rank-one result or challenge submission has been established in this
workspace.

## Branch and campaign map

| Branch or campaign | Main question | Outcome |
|---|---|---|
| `main` | Six-feature UCR/load–phase–unload oracle and later verified improvements | Protected 524/950 fallback; architecture closed |
| `development` | Destructive semantic classifiers, dirty/clean completion, high-order corrections, controlled swaps | Shallow approximate classifiers, but exact completion became thousands of layers; closed |
| `multiplicative-depth` | Exact low-multiplicative-depth XAGs | MD 4 and MD 6 XAGs exist, but native realization remained about 1023/899 or worse; closed |
| `another-one` | Historical phase signals and phase-history spans | Rank improved to roughly 26–29, but the target phase was not in the span; exact phase proposal about 1345/1027; closed |
| `mpo-native-synthesis` | Direct operator synthesis from an exact diagonal MPO/TT | Tensor representation validated, generic optimizers plateaued; merged into `main` as a negative research record |
| `unitary-state-space` | Recast the target as a compressed unitary: finite-size phase states, exact QBPs, TT/MPO dilation, and ZH diagrams | Exact tensor/TT artifacts and bounded probes; no verified improvement, but several misleading abstractions are now closed |
| `three-sweep` | Row-pair loaders, 3+3 and transposed column-pair decoders, phase-rank screens, shell sharing, and reachable parity polynomials | Loaders verified in the 52--65 depth range, but exact decoders were 3802+ depth; closed with no improvement |
| `nonlinear-spectral` | Exact FWHT screen of shallow invertible triangular coordinate mutations and spectral conjugation | Closed the ordinary Walsh-support objective exactly: the odd 1,097-point population forces all 4,096 coefficients nonzero under every permutation |
| `quotient-permutation` | In-place x/y data-register quotient permutations, free class-layout screen, and exact central dyadic phase diagnostic | 11-by-11 quotient is real structure, but the best 61-rectangle central diagnostic was 6456/5490; permutation synthesis was not justified |
| `lut-single-target` | ABC 3/4/5-LUT mappings retained as reversible dirty-target single-target gates, with local U3/CX cost database | Exact mappings found, but the best optimistic forward native critical path was 145 depth; closed before global reversible scheduling |

The merge commit for the MPO campaign is recorded in Git; the branch is
retained for provenance. The current working tree may contain uncommitted
documentation and research-audit files; these are not promoted circuit
artifacts.

### Historical branch refs now merged

The online refs were recovered and merged with
`--allow-unrelated-histories -X ours`, because these two historical branches
share root `95299ba` with each other but not the current repository root. The
merge preserved current `main` versions of overlapping files—especially the
protected implementation and consolidated documentation—while importing
branch-only artifacts, source, tests, and reports. The merge commits are:

```text
c7d1d0c Merge another-one experiment branch into main
a7283b1 Merge multiplicative-depth experiment branch into main
```

The remote-tracking refs remain available as `origin/another-one` and
`origin/multiplicative-depth` for provenance. The imported branch-specific
reports are [`PHASE_HISTORY.md`](PHASE_HISTORY.md),
[`DESTRUCTIVE_CLASSIFIER_PLAN.md`](DESTRUCTIVE_CLASSIFIER_PLAN.md),
[`DESTRUCTIVE_SEMANTIC_SEARCH.md`](DESTRUCTIVE_SEMANTIC_SEARCH.md), and
[`MULTIPLICATIVE_DEPTH.md`](MULTIPLICATIVE_DEPTH.md).

## Verified progression and protected artifacts

| Artifact or architecture | Depth / CX / width | What it established | Disposition |
|---|---:|---|---|
| Original Classiq notebook | 5329 / 3502 / 18 | Correct rectangle-based baseline | Historical baseline |
| `artifacts/xag_rank_True.qasm` | 1046 / 903 | Exact XAG/rank construction | Verified, not competitive |
| Corrected pair construction | 779 / 736 | Pair decomposition can be exact | Verified; earlier apparent 688 was invalid |
| `artifacts/radius_mux.qasm` | 682 / 740 | Shared-radius UCR architecture | Verified, superseded |
| Parallel six-feature UCR | 536 / 1020 | Major architectural breakthrough | Verified, superseded |
| `artifacts/524/full_mux_feature_linear_tket_524.qasm` | **524 / 950 / 18** | Affine feature assignment plus safe post-processing | **Protected fallback** |
| Packaged `artifacts/531/` deliverable | 531 / 1020 / 18 | Earlier packaged fallback/QMOD pair | Preserved; not current local best |
| Disjoint geometry | 708 / 752 / 18 | Exact A, B', C, D geometric decomposition | Verified negative |

The 524 file is never overwritten by experiments. New candidates must use new
paths and matching verification reports.

## Method inventory

### Exact destructive classifier + one phase (September 11, 2026)

The first falsification checkpoint is implemented in `src/destructive_xag.py`.
The original-coordinate 97-AND XAG is exact over all 4096 points, but a
bounded topological allocator that gives each nonlinear signal one physical
wire observes a minimum peak of **22 live registers**. With one wire reserved
for the predicate, only 17 signal wires are available, so the straightforward
one-pass compiler cannot fit. It also runs out of registers at node 22 before
QASM lowering. This is a negative result only for the one-signal-per-wire
lowering; the intended affine-frame packing/recomputation variant remains
untested. The report is `artifacts/destructive_xag_register_pressure.json`.
The exact GF(2) follow-up finds maximum affine live-rank **34** in the
original topological order, so affine packing alone cannot fit that order into
18 wires. The best one-pass ready-node schedule lowers the observed rank to
about 22, making scheduling, dirty targets, and bounded recomputation the next
tests. The cut-by-cut report is `artifacts/destructive_xag_affine_rank.json`.
The first bounded rank-constrained rematerialization screen tested budgets 0,
4, 8, 12, 20, and 30 with no phase frontier found. It remains a heuristic
negative result rather than an impossibility proof; its trace is
`artifacts/destructive_xag_scheduler_rank19_beam50.json` and its source is
`src/destructive_xag_scheduler.py`.
The scheduler's affine capacity is corrected to rank 19: 18 physical wire
functions plus the free constant-one offset.

The corrected beam-50 rerun remained negative at budgets through 30. A separate
physical dirty-span prototype, which applies (h\mapsto h\oplus(a b)) to the
actual affine basis, reached 36 guided products without an exact phase
frontier. Both are bounded heuristic screens; neither is an impossibility
proof. The physical prototype is `src/destructive_dirty_search.py`.
The final repeated-product variant removed the one-use restriction and ran to
120 evaluations at beam 50 without a phase frontier; it repeatedly used only
nine products and reached 20 output-cone signals. Its reports are the
`destructive_dirty_search_repeated_beam50_*` artifacts.

### Three-sweep campaign

The complete September 11 record is [`THREE_SWEEP.md`](THREE_SWEEP.md). It
contains the construction, source/artifact map, exhaustive reports, research
interpretation, and the distinction between verified subcircuits, exact but
uncompetitive full oracles, and unresolved hypotheses.

### 1. Direct Classiq and notebook synthesis

The original notebook decomposed the logo into disjoint rectangles and used
Classiq synthesis. It established correctness but produced depth 5329.
Later Classiq-native attempts included arithmetic, lookup, direct geometry,
row-class, and low-rank models. Arithmetic required 82 qubits; bounded row and
low-rank requests did not return useful fresh QASM. These are backend/model
experiments, not evidence that Classiq is incapable of all future solutions.

Details: [`EXPERIMENTS.md`](EXPERIMENTS.md), Classiq sections;
[`HANDOFF.md`](HANDOFF.md), “Classiq-native campaign closure”.

### 2. Pair, radius, UCR, and feature-frame architectures

The central successful line loads y-dependent features into clean ancillas,
applies x-controlled phase operations, and uncomputes the features. It
progressed through pair circuits, shared radius multiplexors, six parallel
features `(R0,R1,R2,A,B,V)`, physical feature permutations, and a GF(2)
affine output frame. Pytket post-processing and safe rebasing produced the
protected 524 result.

The failure mechanism is now measured: q16 in the protected file participates
in 405 operations, including 206 CX gates. The fixed gate multiset therefore
has a 405-layer per-wire scheduling floor. This is not a lower bound on a new
unitary, but it closes seed/order/compiler tuning for this architecture.

Details: [`CURRENT_DESIGN.md`](CURRENT_DESIGN.md),
[`HYBRID_AFFINE_REPORT.md`](HYBRID_AFFINE_REPORT.md), and the UCR sections of
[`EXPERIMENTS.md`](EXPERIMENTS.md).

### 3. Rank, XAG, ANF, ESOP, and Boolean factoring

The rank-factor and XAG campaigns searched for low-AND representations of
Boolean features and phase terms. They included minimum-MC rank banks,
multi-output XAGs, affine transport, min-MC searches, exact formula factoring,
shared-XAG pebbling, and direct ESOP covers.

They reduced classical expression size but not native depth: recomputation,
live-value lifetime, relative phases, and six-ancilla scheduling dominated.
The best exact XAG-family realization remained far above the protected result.

Details: [`MINMC_RANK_REPORT.md`](MINMC_RANK_REPORT.md),
[`HYBRID_AFFINE_REPORT.md`](HYBRID_AFFINE_REPORT.md),
[`PHASE_PEBBLE_REPORT.md`](PHASE_PEBBLE_REPORT.md), and the Boolean sections of
[`EXPERIMENTS.md`](EXPERIMENTS.md).

### 4. Destructive semantic classifiers and phase histories

The `development` campaign allowed writable data wires and searched for
approximate classifiers, affine residuals, high-order corrections, dirty and
clean completion, signed controls, Fredkin/controlled-swap variants, and
local RCCX neighborhoods. It independently self-tested the semantic
implementation over all 4096 inputs.

The best forward residuals improved through approximately `(depth, residual)`
79/331, 90/315, 108/279, and 146/197, but residual here is an affine truth
table distance, not circuit depth. Exact completion expanded catastrophically.
The local screens included 2,448 one-RCCX neighbors and degree-3 through
degree-6 monomial screens without an escape.

The `another-one` campaign retained historical Boolean phase signals rather
than requiring a final classical classifier. Ranks around 26–29 were reached,
but the exact logo phase was not in the generated spans. This is why more beam
width or more phase-history ordering is not justified.

Details: [`HANDOFF.md`](HANDOFF.md), “Cross-branch strategic closure”; the
development and phase-history sections of [`EXPERIMENTS.md`](EXPERIMENTS.md).

### 5. Multiplicative-depth and low-depth XAGs

Exact XAG search found an MD=4 construction with 5096 ANDs and a much smaller
81-AND construction at MD=6. Their native quantum realizations were still
about 1023/899 or worse. This separated multiplicative depth from scored
`u3`/`cx` depth: affine transport, ancilla lifetime, recomputation, and
relative-phase-safe lowering dominate.

Details: the multiplicative-depth entries in [`HANDOFF.md`](HANDOFF.md) and
[`EXPERIMENTS.md`](EXPERIMENTS.md).

### 6. Geometry and disjoint-component decompositions

The exact union was rewritten as square A XOR bar-with-overlap-removed B'
XOR disk C XOR disk D. Standalone blocks, all six composition orders, direct
interval rectangles, bounded shared rectangle bases, separate-disk loaders,
and interleaved pair banks were measured.

The best complete result was about 649/727 after bounded post-processing, and
the primary disjoint composition was 708/752. Independent blocks serialize;
the route needs a genuinely shared/interleaved phase primitive and is closed
in its current form.

Details: [`DISJOINT_GEOMETRY_REPORT.md`](DISJOINT_GEOMETRY_REPORT.md).

### 7. Threshold, shell, Shannon, row-class, and vector loaders

The experiments tested replacing binary radius bits with threshold/parity
flags, deriving `B = y5 AND T`, splitting radius tables by retained y5,
Shannon trees, QROM trees, row-class codes, five-output vector loaders,
direct output accumulators, dirty relative-phase loaders, persistent frames,
and multiple affine input/output bases.

The key failures were architectural rather than algebraic:

- direct threshold-conditioned shell phase cubes: verified but 4437/3854;
- five-input Shannon radius split: verified but 969/1244;
- QROM-tree and lookup variants: correct but not competitive;
- five-output vector loader: exact loader structures did not integrate cheaply;
- a transient five-output diagnostic had an x-dependent zero-branch phase and
  was rejected until corrected;
- persistent output-frame integration reached about 2032/1425.

The current exact research audit finds that retaining y5 permits seven and
six row classes with three additional *abstract* bits, but a shared code over
low five y bits must distinguish 18 ordered row-pair classes and therefore
needs at least five bits in that model. A bounded physical three-bit screen
found `(y2,y3,y4)` still caused 8 low-half and 6 high-half row collisions.

Details: [`VECTOR_LOADER_REPORT.md`](VECTOR_LOADER_REPORT.md),
[`RESEARCH_REVIEW_2026-09-09.md`](RESEARCH_REVIEW_2026-09-09.md), and the
loader sections of [`EXPERIMENTS.md`](EXPERIMENTS.md).

### 8. BDD, cofactor, semantic-window, and conditionally-clean methods

The target has roughly 91 nonterminal states under one useful reduced BDD
order, but naive reversible BDD materialization exceeded six clean ancillas.
Cofactor mining, rank banks, product-phase streaming, one-live-pair and
two-live-pair schedules, HP24 lowering, and conditional-clean selectors were
implemented and verified on selected components.

The best local conditional-clean/factored branch was about 713/445; its
component ablations were 323/249 and 459/248, but complete integration was
not competitive. The branch invariant was useful, but independently applying
it to each cofactor recreated the compute/phase/uncompute bottleneck.

Semantic-window and BQSKit/StateSystem pilots either exceeded bounded runtime,
returned state-limit/unknown, or produced no native candidate. These are
bounded solver results, not impossibility proofs.

Details: [`PHASE_PEBBLE_REPORT.md`](PHASE_PEBBLE_REPORT.md),
[`REASSESSMENT_2026-09-09.md`](REASSESSMENT_2026-09-09.md), and the cofactor,
BDD, and semantic sections of [`EXPERIMENTS.md`](EXPERIMENTS.md).

### 9. Persistent frames, retained products, and phase-aware pebbling

These methods attempted to retain computed values across multiple phase taps,
share nonlinear products, and clear a common semantic frame only once. They
included phase-edge retention, persistent parity, retained products,
global-endpoint identities, exact one-live-pair/two-live-pair streams, and
dynamic six-ancilla planners.

They established correct lifetime and phase-cancellation invariants for
selected components. Complete-oracle compositions remained well above the
protected result; sharing a Boolean subtree without a global reversible
pebbling schedule did not save depth.

Details: [`PHASE_RETENTION_REPORT.md`](PHASE_RETENTION_REPORT.md),
[`TWO_HOUR_CLOSURE_REPORT.md`](TWO_HOUR_CLOSURE_REPORT.md), and
[`EXPERIMENTS.md`](EXPERIMENTS.md).

### 10. Rewriting and external reversible-synthesis stacks

Bounded PyZX, pytket peephole/full optimization, global pass composition,
PyZX extraction, GraySynth/Walsh synthesis, Tweedledum/RevKit, Synthetiq,
BQSKit local windows, and GUOQ/QUESO compatibility were tested or audited.

Pytket supplied the useful 524-scale post-processing improvement. The other
rewriting and synthesis stacks either reproduced the same direct MCZ/ESOP
regime, exceeded bounded runtime, lacked a suitable depth objective, failed
compatibility, or produced no candidate. No backend metric is accepted unless
the final serialized QASM is independently verified.

Details: [`EXPERIMENTS.md`](EXPERIMENTS.md),
[`OVERNIGHT_REPORT.md`](OVERNIGHT_REPORT.md), and the external-stack sections
of [`HANDOFF.md`](HANDOFF.md).

### 11. QFT/arithmetic coordinate recoding

`src/qft_recenter.py` exactly implements a conditional low-five-bit modular
recenter and verifies all 64 y inputs. Its standalone cost is 81/58. A full
oracle would need a forward/inverse pair, leaving roughly 162 depth before
the logo phase, so the coordinate-recoding/staircase architecture was closed.

Details: the QFT sections of [`EXPERIMENTS.md`](EXPERIMENTS.md) and
[`REASSESSMENT_2026-09-09.md`](REASSESSMENT_2026-09-09.md).

### 12. Direct operator-native MPO/TT synthesis

The MPO campaign changed the mathematical object: it represented the exact
diagonal sign operator directly, with marked-state count 1097, x|y matrix
rank 11, and maximum TT rank 13 in an interleaved bit order. Exact MPO
contraction and non-adjacent gate application were validated against dense
evaluation.

The following optimizers were tested:

- adjacent brick-wall/RieADAM: plateau near process fidelity 0.302;
- non-chain autodiff capability test: 0.17246 to 0.19172;
- gatewise Procrustes: best 0.36985 at six round-robin layers;
- four-ancilla bus sweeps: 0.265659;
- sequential 32x32 memory blocks: 0.266116–0.266156;
- Riemannian control: no improvement over gatewise sweeps;
- analytic SU(4) Adam: exact fidelity 0.6616 at 40 layers, compiling to
  depth 241 / 720 CX;
- analytic four-ancilla bus Adam: estimated fidelity 0.373421.

The depth-17/48 approximate QASM was correctly rejected by exhaustive
promotion with phase error about 2. No MPO candidate was promoted. The
conclusion is specific: generic SU(4)/MPO optimization is not competitive;
the exact low tensor rank remains structural information, not a circuit-depth
bound.

Details: [`MPO_NATIVE_SYNTHESIS.md`](MPO_NATIVE_SYNTHESIS.md).

### 13. Unitary/state-space rethink

The September 11 research program asked whether the missing circuit class is
best described by a compressed unitary rather than a Boolean classifier. It
contains four bounded directions: a finite-size audit of phase-state/quantum
branching-program ideas, exact finite-group QBP searches with symmetry and
meet-in-the-middle checks, exact TT-rank plus same-bond unitary-dilation
diagnostics, and a direct ZH graph for all 1,097 marked truth-table points.

The exact tensor is genuinely structured (maximum TT rank 13), but the
same-bond row-isometry test fails at several layers. The QBP and ZH probes
generated useful artifacts and tests, yet neither yielded a verified oracle or
a compact native `u3`/`cx` implementation. The correct disposition is a
documented research closure, not an impossibility claim: a future breakthrough
needs a new algebraic/unitary representation or a concrete external clue about
the leaderboard construction.

Details: [`UNITARY_STATE_SPACE.md`](UNITARY_STATE_SPACE.md),
[`RESEARCH_REVIEW_2026-09-09.md`](RESEARCH_REVIEW_2026-09-09.md), and the
source packages under `src/qbp/`, `src/tt_unitary/`, and `src/zh_direct/`.

## Research references and how they were used

These references informed bounded experiments; none is evidence that this
specific target has a sub-200 solution.

| Reference | Used for | Local interpretation |
|---|---|---|
| Bergholm, Vartiainen, Möttönen, Salomaa, [uniformly controlled gates](https://arxiv.org/abs/quant-ph/0410066) | UCR/Walsh lookup decompositions | Explains regular multiplexor costs; does not prove optimality |
| Seidel et al., [phase-tolerant oracle synthesis](https://arxiv.org/abs/2110.07545) | Relative-phase loading/uncomputation | Savings apply only with explicit phase-cancellation invariants |
| Khattar and Gidney, [conditionally clean ancillas](https://arxiv.org/html/2407.17966v2) | Borrowed/conditionally clean workspace and unary iteration | Requires a proven branch promise; ordinary dirty scratch is not equivalent |
| Amy and Ross, [phase/state duality](https://arxiv.org/abs/2105.13410) | Relative-phase compute/phase/uncompute reasoning | Valid only for the complete intervening operation and restored borrowed controls |
| Synthetiq, [partial-specification synthesis](https://files.sri.inf.ethz.ch/website/papers/paradis2024synthetiq.pdf) | Small partial-state/operator kernels | Audited as a possible local tool; no complete competitive candidate |
| Zhu, Sundaram, Low, [unified QROM architecture](https://arxiv.org/abs/2406.18030) | Lookup space/depth tradeoffs | Extra routing and workspace must be counted at the six-ancilla ceiling |
| Nie and Zi, [Boolean-oracle tradeoffs](https://arxiv.org/html/2607.28402v1) | Recent asymptotic context | Family-level bounds do not establish this fixed instance's score |
| Classiq, [uncomputation](https://docs.classiq.io/qmod-reference/language-reference/uncomputation) | Native compute/apply/uncompute models | Backend reference, not a substitute for exported-QASM verification |
| INMLe, [rqcopt-mpo](https://github.com/INMLe/rqcopt-mpo) | Operator-level MPO optimization | Adapted and tested locally; generic optimizer was negative |

## What is proven, what is not

### Proven or directly verified

- The protected QASM is exact under the repository verifier and its report
  matches its SHA.
- The exact target has 1097 marked coordinates and the stated MPO/TT ranks.
- The documented candidate QASM files that have matching exhaustive reports
  are correct for all 4096 basis inputs, within the verifier tolerance.
- The listed approximate MPO circuits are approximate and must not be called
  oracle candidates.
- The searched architecture families have concrete measured failure modes.

### Not proven

- No lower bound proves that depth 183, 197, or 150 is impossible.
- No tensor rank, Boolean rank, AND count, BDD size, or T-depth is a native
  `u3`/`cx` depth lower bound for every possible circuit.
- The absence of a public leader implementation is not evidence about its
  construction.
- A local improvement would not establish rank one; the live leaderboard and
  submission state must be checked separately.

## Reproduction and handoff rules

Read this file together with [`HANDOFF.md`](HANDOFF.md),
[`CURRENT_DESIGN.md`](CURRENT_DESIGN.md), and the chronological
[`EXPERIMENTS.md`](EXPERIMENTS.md). Use `.venv/bin/python` from the repository
root. Do not run scripts known to overwrite protected artifacts. Generate new
candidate names, compile with `qubits_initially_zero=False`, verify the exact
serialized QASM, and record depth, CX count, width, SHA, command, and status.
