# Experiment history and failure notes

## Disjoint geometry architecture (September 9, 2026)

The exact geometric rewrite `A XOR B' XOR C XOR D` was checked over all 4096
points with zero mismatches and pairwise overlap counts all zero. A and B'
were compiled as standalone pair phase blocks at 160/122 and 161/145 depth/CX.
The disk-only C XOR D block loads only R0/R1/R2, derives V as R1 OR R2, uses a
free q16 phase helper, and measures 385/491/18. Its exact QASM is
`artifacts/disk_only_mux.qasm` and its exhaustive report has SHA
`46be9e4d583017db29cc18da2c3023658aa67d4394fa1063e2ebd286866e8bf5`.

Composing the three blocks in all six orders produced the verified best
`artifacts/disjoint_geometry_708.qasm` at **708 depth / 752 CX / width 18**,
order disk, B_prime, A, SHA
`e6bf58e1782a484168da7eafbbdedd8652004e3fd18ff5c450e9365e1c9f3c3c`.
Direct interval rectangles and bounded direct/hybrid radius-bit loading were
worse. This closes the disjoint-component architecture as a negative result
against the protected 531 depth, while identifying shared/interleaved phase
loading as the only remaining meaningful follow-up.

The bounded interleaving follow-up was also negative. The pair compiler could
not realize either rectangle with only three clean ancillas, preventing two
independent rectangle banks. A two-output rectangle multiplexer measured
384/372 depth/CX alone and 767/863 when composed with the disk block. No
further ordering or seed search is justified for this architecture.

## Overnight shared-pair diagnostics (September 8, 2026)

The first bounded experiment on the shared-XAG path was `src/global_pair_compile.py`.
It selected the same locally best pair constructions used by `pair_search.py`,
but composed their raw circuits before one global U3/CX transpilation. This
tests whether independent pair-block boundaries were preventing cancellation.
The exact exported candidate `artifacts/global_pair_raw.qasm` was exhaustively
verified on all 4,096 inputs (zero ancilla leakage), but scored depth **844** /
**781 CX**, versus the existing pair result of 779 / 736. Ordinary global
composition is therefore a negative result and does not justify more of the
same transpiler-only search.

A manual two-term sharing prototype was also attempted on rank terms 1 and 4,
which share the x-factor `(~x4 & x5)`. Retaining that factor live caused the
remaining formula computation to exceed the available scratch schedule. This
is evidence that useful sharing requires an explicit reversible pebbling
algorithm; factoring a common Boolean subtree alone is insufficient under the
six-ancilla ceiling.

A bounded order sweep over the existing shared-XAG planner was then scored by
actual serialized depth. The best clearing schedule used term order
`[5,2,0,9,7,3,8,4,1,6]` and reached depth **1035** / **899 CX**; the best
retain-all schedule reached depth **1337** / **1023 CX**. Both exact QASM files
passed exhaustive verification. Term ordering alone is therefore closed as a
route to the 531 baseline; the next change must improve the nonlinear
representation or its pebbling transitions.

## Joint alternative-pair pebbling (September 8, 2026)

`src/shared_alternative_pair.py` searches factorized phase forms for two roots
jointly, pebbles the union of their nonlinear nodes once, applies both phase
terms while the shared values are live, and then clears the union. On the
optimized `artifacts/pair_terms.json` basis, the best observed local block was
terms `(0,1)` at depth 136 / 136 CX, which is already worse than independently
composing those two terms at depth 91 / 102 CX.

However, replacing those two terms inside the complete ten-term oracle and
then globally rebasing produced the exact candidate
`artifacts/pair_shared_0_1.qasm` at depth **821** / **770 CX**. Exhaustive
verification passed with zero ancilla leakage. The current pair baseline
remains 779 / 736, so local joint-pair depth is not predictive of full-oracle
depth. The next useful extension is a multi-group scheduler that optimizes
the ordering and shared phase/CNOT boundaries across all groups, rather than
independent replacement of one pair.

The two-group follow-up, combining local blocks `(0,1)` and `(6,8)`, reached
depth **865** / **827 CX** and passed exhaustive verification. Independently
optimized shared groups therefore do not compose constructively; the next
compiler must schedule the complete phase network globally.

## Quadrant-specific rank decomposition (September 8, 2026)

The quadrant-rank structural claim was independently reconstructed. The four
quadrants `(x5,y5)` have exact GF(2) ranks **1, 2, 5, 4**, respectively, for a
total of 12 rank-1 terms. The corrected source is `src/quadrant_rank.py` and
checks the classical factorization pointwise before compilation.

Compiling those selector-aware terms through the existing pair machinery gave
`artifacts/quadrant_rank.qasm` at depth **1057** / **952 CX** / width 18. The
serialized QASM passed exhaustive verification with zero ancilla leakage, so
the decomposition is correct but its naive reversible realization is far worse
than the 531-depth baseline. The rank structure needs a specialized quadrant
loading/phase primitive to become useful.

A specialized follow-up, `src/quadrant_phase.py`, computed each factor only
on the five low bits and used `x5`/`y5` as direct phase controls. Its first
prototype had an invalid repeated-compute uncompute; the corrected version
uses actual inverse subcircuits and is exhaustively verified at depth **1394** /
**1054 CX**. Direct selector controls therefore do not make sequential
quadrant phase terms competitive.

## PyZX extraction diagnostic (September 8, 2026)

PyZX `full_reduce` followed by its supported `extract_circuit` routine was
run on the protected depth-531 QASM. Extraction succeeded, but the result
expanded to 5,788 native gates and rebased to depth **2655** / **3022 CX**.
Its sparse exhaustive verifier exceeded the support limit, so it was not
accepted as a candidate. PyZX extraction is closed as a useful optimization
path for this circuit.

## Actual compiled rank-basis search (September 8, 2026)

`src/actual_pair_basis_search.py` performed 60 rank-basis mutations starting
from `artifacts/pair_terms.json`, scoring each complete serialized U3/CX
oracle rather than a sum of local pair costs. Several mutations were
uncompilable; the best accepted transient state was depth 783 / 724 CX. No
candidate improved the trusted 779 / 736 pair baseline, so this closes the
remaining GL-basis proxy concern without producing a better circuit.

A different schedule retained two complete x-side rank factors in ancillas,
streamed their y-side factors through one target ancilla, and uncomputed the x
bank once. The best feasible group tested, `(0,3)`, produced a full verified
oracle at depth **892** / **783 CX**. Reusing complete factors across terms is
therefore also negative under the six-ancilla budget.

Numbers below are historical observations unless explicitly marked verified. Most experimental artifacts remain in `artifacts/` for investigation; their existence does not establish validity. See the handoff for the four trusted milestones and the compiler-initialization bug.

## Development branch joint-rank feasibility diagnostic (September 9, 2026)

The proposed three-term, 3+3-ancilla rank batch was tested against the
repository's exact XAG pebble planner. No pair or triple from any of
`rank_terms`, `pair_terms`, or `rank_mc_pareto_terms` was jointly feasible with
three live ancillas on each side. At a four-ancilla limit, many pairs were
feasible, but no triples were feasible. The reproducible scan is
`src/joint_rank_feasibility.py`, with output in
`artifacts/joint_rank_feasibility_development.json`.

A bounded elementary rank-basis mutation screen then tested 40 mutated bases
and 480 sampled pairs under the three-ancilla limit. It found no feasible pair;
the diagnostic output is `artifacts/joint_rank_basis_search_development.json`.
This is not an impossibility proof: the screen uses the existing formula/XAG
representation and a bounded planner state budget. It does establish that the
original basis cannot be passed directly to the proposed 3+3 prototype, so a
new multi-output or phase/state synthesis primitive is required before a full
rank-batching oracle is attempted.

## Development phase-state and rank-batch probes (September 9, 2026)

Two bounded probes were checked against the exact serialized product semantics.
The synchronized three-term rank batch in `src/rank_batch_ucr.py` computes three
x-side factors and three y-side factors in disjoint three-wire banks, applies
three CZ phase edges, and clears both banks.  The selected batch `(0, 1, 2)`
from `rank_terms` is exact on all 4,096 coordinate inputs at **257 depth / 535
CX / 18 qubits**, with zero ancilla leakage.  Its report and SHA-matched QASM
are `artifacts/rank_batch_ucr_012_development.product.exhaustive.json` and
`artifacts/rank_batch_ucr_012_development.qasm`.  It is not a complete oracle:
ten rank terms would require multiple serialized batches, so this does not
replace the protected 524-depth circuit.

The phase-state retention probe in `src/direct_product_retention.py` retains
one x product factor while streaming y phase edges.  The exact compute version
for rank term 0 is exhaustively checked at **222 depth / 225 CX / 18 qubits**
with zero ancilla leakage; the matching report is
`artifacts/direct_product_retention_term0_exact_development.exhaustive.json`.
This is a single-term primitive only.  The lower 162-depth development variant
was not accepted because it predates the exact relative-phase check and is not
used as a claimed result.

## Development branch retained-product pilot (September 9, 2026)

For rank term 0, a retained-product schedule kept the nonlinear x-root live
while streaming the eight y-side phase edges. The first 162-depth version used
RCCX toggles and a pooled planner that allowed unrelated temporaries to remain
live between edges. It failed the full-logo verifier, as expected for a
partial term, and also failed the product-term verifier due to an actual
relative-phase error. It is retained as
`artifacts/direct_product_retention_term0_development.qasm` only as a failed
diagnostic.

The schedule was tightened to require the exact retained live set after each
edge and to use exact CCX toggles. The resulting standalone term circuit is
`artifacts/direct_product_retention_term0_exact_v2_development.qasm`, with
depth **508**, **407 CX**, and width 18. It passed the new
`src/verify_product_term.py` exhaustive check on all 4096 inputs for the
mathematical target `(-1)^(a_0(x)b_0(y))`, with maximum error
`5.73e-15` and zero ancilla leakage. Its SHA-256 is
`4847944094e71f419e4574ee689cdcb535f39a014c0729b760b7b185815faca5`.
This is a correctness baseline, not a full-logo improvement; exact cleanup
removes the apparent low-depth advantage.

## Development branch three-term UCR batch (September 9, 2026)

`src/rank_batch_ucr.py` implements the proposed 3+3 architecture directly:
three synchronized x-side UCR loads, three synchronized y-side UCR loads,
three parallel CZ couplings, and exact inverse UCR cleanup. For rank terms
`(0,1,2)`, the serialized standalone batch
`artifacts/rank_batch_ucr_012_development.qasm` measures **257 depth / 535 CX /
18 qubits**. A seed screen over seeds 0--7 kept depth fixed at 257 (CX range
511--555), indicating that the UCR schedule depth is structural rather than
an ordering accident.

The candidate passed `src/verify_product_term.py` against the XOR of those
three rank products on all 4096 inputs, with maximum error `1.27e-14` and
ancilla leakage `2.18e-15`. Its SHA-256 is
`cdb69043c2f87599b203881d40377332e2066ad4d99a49d5c8fdb43a7a395410`.
This validates the batch architecture as a partial oracle, but four such
batches would exceed the target. The next useful improvement must reduce the
per-bank load depth below the UCR ~128-layer regime or combine batches without
repeating full load/unload stages.

An ESOP alternative, `src/rank_batch_esop_dirty.py`, used the other five
ancillas as dirty scratch while loading each of the three outputs. It compiled
to **672 depth / 433 CX**, but failed the three-term exhaustive phase check
with error 2. The retained-output relative phases do not cancel across the
multi-output load sequence. Its artifact is retained as
`artifacts/rank_batch_esop_dirty_012_development.qasm` only as a negative
diagnostic.

A five-factor streamed-bank variant was also tested in
`src/rank_batch_streamed.py`: five x-factors were loaded once with UCR, and
each y-factor was loaded into the remaining ancilla using the retained x-bank
as dirty scratch. The candidate measured **753 depth / 781 CX**, but failed
the five-term exhaustive product check with phase error 2. Thus the current
relative-phase predicate loader cannot safely stream a factor across a live
bank; exact phase-safe loading is still required.

## Boolean decomposition and reversible logic

| Files | Approach | Outcome / limitation |
|---|---|---|
| `search.py` | 64x64 truth mask, 6-bit ESOP with Shannon and positive/negative Davio choices; row and nested rectangle factors; relative-phase MCX chains | Initial circuits about 2599/2653 depth. Useful predicate and decomposition utilities remain foundational. |
| `formula.py` | Boolean AST with AND/XOR/NOT, disjoint-support decomposition, Shannon/Davio recursion minimizing ANDs | Classical AND count did not predict reversible depth; child compute/uncompute was expensive. |
| `pebble.py` | Smarter recursive computation and retaining temporary nodes | About 1746 depth, insufficient improvement. |
| `factor.py` | Global signed-literal phase ESOP, common-pair factoring | About 1900 depth; high-control phase tails costly. |
| `structured.py` | Shared expression factors | Attempted construction ran out of scratch space. |
| `stream.py` | Stream deltas between successive predicates | Worse than simpler decompositions. |
| `rank.py` | GF(2) rank-10 matrix factorization; randomized basis changes preserving XOR of x/y factor products | About 1409 with earlier compiler; `rank_terms.json` remains useful input. |
| `affine.py` | Search coordinate CNOT transforms reducing predicate AND count | Modest reductions; `affine_formulas.pkl` caches expressions. |
| `xag.py` | XOR-AND graph with truth-based reuse, affine forms, A* reversible pebbling under six-live-node limit | `xag_rank_True.qasm` verified depth 1046 / CX 903. |
| `xag_basis.py` | Allow denser linear-span reuse (up to 3 terms) | Increased dependencies/pebbling burden; no gain. |
| `xag_phase.py` | Open AND roots into multi-factor phase conditions; synthesize affine phase constraints directly | Useful building block but standalone variants not best. |
| `xag_affine.py`, `xag_mcz.py` | Affine transformations and alternate MCZ synthesis in XAG phases | Some promising old values were invalid due to default clean-input assumption. Rebuild and verify before reuse. |
| `pair_search.py` | Fresh graph per factor pair, avoiding cross-predicate dependencies; phase expansions; 300 randomized basis updates | Corrected best `pair.qasm` depth 779 / CX 736, exhaustively verified. Old depth 688 was invalid and overwritten. |
| `static_cache.py` | Keep frequent leaf ANDs live across pairs | No established useful improvement; old ~770 observation not a trusted milestone. |
| `translate.py` | Modular coordinate translations and inverse before predicates | Adder overhead prevented beating 779. |
| `mcz.py` | Compare clean/dirty/no-aux Qiskit MCX decompositions, wrap as signed MCZ | Important utility. Every inner transpilation must use `qubits_initially_zero=False`. |
| `debug_phase.py` | Test isolated pair phase expansions | Located phase-error-2 bug; all ten tested terms passed after initialization fix. |

`search.py` supplies 10 distinct row patterns and 11 telescoping nested factor pairs. In nested decomposition, the bar becomes x=27..48 because x=26 overlaps the square and x=49 belongs to D1. `check_terms` checks the XOR reconstruction exactly.

XAG details: affine forms are frozensets; -1 means constant one, IDs 0..11 are inputs, IDs >=12 are AND nodes. A* toggles a node only when its parents are live; at most six ancilla nodes are live. Dense linear reuse can look cheap algebraically while making cleanup expensive. Relative-phase RCCX compute/uncompute is used only where phases cancel around the intervening diagonal operation.

## ABC minimization

- Built official Berkeley ABC locally in `experiments/abc`.
- Global logo PLA/ESOP: `experiments/logo.pla`, `experiments/logo.esop`; exorcism produced 57 cubes / 507 literals. Direct circuit compilation did not become the best approach.
- Radius multi-output PLA/ESOP: `experiments/radius.pla`, `experiments/radius.esop`; 13 cubes / 59 literals. Lookup still too deep after reversible implementation.

## Shared radius and multiplexor designs

| Files | Approach | Outcome |
|---|---|---|
| `radius.py` | Encode both disks by one 3-bit radius(y), with separate radius-8 boundary correction | Key architectural improvement. |
| `radius_circuit.py` | Multi-output ABC ESOP lookup, output basis search, factored relative controls, shared comparator | Full circuit about 847 depth, historical result. |
| `qrom_tree.py` | Vector Shannon/Davio dynamic program; unary iteration reuses parent condition between siblings | Lookup depth 171 / CX 106; full about 777, historical result. |
| `radius_mux.py` | Three parallel uniformly controlled RY lookups, cyclic control orders, shared radius comparator | Verified depth 682 / CX 740; seed 3. |
| `full_mux.py` | Six parallel RY outputs plus three parallel RZ phase lookups for left shapes, shared comparator, correction pair | **Verified depth 536 / CX 1020**, seed 94. Current best. |

## Row-class encoding prototype (September 8, 2026)

The exact logo has 11 distinct row patterns: one blank class and two nested
five-level families. A first prototype in `src/class_oracle.py` encoded those
classes into feature ancillas, loaded them with parallel multiplexors, and
expanded each class's x-mask independently into phase cubes. This is a
correctness-verified negative result, not a candidate improvement:

| Artifact | Encoding | Depth | CX | Verification |
|---|---|---:|---:|---|
| `artifacts/class_binary4_proto.qasm` | 4-bit class index | 3715 | 3084 | Exhaustive; SHA in report |
| `artifacts/class_thermometer5_proto.qasm` | 5-bit family + level index | 4174 | 3676 | Exhaustive; SHA in report |
| `artifacts/class_nested5_proto.qasm` | 5-bit family/active/level with shared shell phases | 4105 | 3498 | Exhaustive; SHA `71260b87d36a5c553db48f815c7274cf1cb8411afbcdd5a92d4fc2a6d55ac343` |
| `artifacts/class_nested5_transposed.qasm` | Same decoder using column classes | 6958 | 5648 | Exhaustive; SHA `ce7ebb17bb8ba4c665cd23e731687f39bf2dca432821d9c77133727688d10f32` |
| `artifacts/class_nested5_codebook_search.qasm` | Best of 80 valid 3-bit level-code assignments; `(0,4,5,7,6)` | 4079 | 3568 | Exhaustive; SHA `890cfb8e55fdfb6dedba98ab255ab63337e72255478bf2167e17cec42a4ff422` |
| `artifacts/class_nested4_structured.qasm` | 4-bit family bit plus nonzero 3-bit level code | 5002 | 3686 | Exhaustive; SHA `e3a8ef621754a88b177c5bd5229f1be9e9541d3267e628f781940c174c9246e2` |
| `artifacts/class_espresso4.qasm` | 4-bit Espresso don't-care cover plus exact residual | 5829 | 4322 | Exhaustive; SHA `4c4c6e9b3e0c077df30ac542313e5053c79c27beb8fefa9c7640473956c7d14b` |
| `artifacts/class_espresso5.qasm` | 5-bit Espresso don't-care cover plus exact residual | 5887 | 4884 | Exhaustive; SHA `c9203cbe5166ee9937bc62f980e20dbce5572c8a1f5c285252bd803661fc21ba` |

The shared-shell version is correct but still poor. The improvement over the
naive decoder is small because each shell/threshold term is still emitted as a
separate high-control phase cube. The next version must synthesize threshold
features as reusable reversible values, rather than expanding their ESOP terms
independently. A separate global GraySynth parity-polynomial benchmark was also
poor: the 4-bit central relation synthesized to depth 1743 and the 5-bit
relation to depth 3479 before feature load/unload. The transposed class layout
was worse than the row layout, so row classes remain the preferred direction.
Espresso reduced the OR cover using unreachable codes, but exact phase parity
residuals made the resulting circuits worse than the shared-shell construction.
An XAG attempt to compute the full 10-input 4-bit decoder into dirty workspace
did not produce an artifact: the reversible-pebbling search exceeded 500,000
states even when all six original y wires plus q[16:17] were available as
workspace. This remains a possible future optimization, but is not a verified
candidate.

The gain comes from parallel depth, even though the new best uses more CX gates than the previous best. Read `CURRENT_DESIGN.md` before changing the phase trick or comparator.

## Classiq synthesis experiments

## Phase-aware dynamic six-ancilla compiler

`src/phase_pebble_rank.py` tested the requested architecture in which rank
factor roots are expanded into GF(2)-cancelled phase edges and nonlinear XAG
nodes are dynamically computed from one shared pool of six clean ancillas.
All 30 rows across `pair_terms`, `rank_terms`, and `rank_mc_pareto_terms` were
feasible; exact pair metrics are recorded in
`artifacts/phase_pebble_pair_metrics.json`. The complete independent-edge
`rank_mc_pareto_terms` oracle was exhaustively verified at **depth 3163 / 3318
CX / width 18**, so it is correct but far worse than the protected 531-depth
best. The bottleneck is per-edge recomputation. See
`docs/PHASE_PEBBLE_REPORT.md` for the full result and next path.

## Phase-edge retention search

The pooled retention compiler in `src/phase_retention.py` completed the
required greedy, beam-64/256/1024, and term-6/term-7 local-order searches.
Term 7 improved from 728/683 to **202/223** depth/CX and term 6 from 563/502
to **186/182**. The complete ten-term retained oracle, after 100 term-order
permutations, was exhaustively verified at **1818/2070/18** (depth/CX/width).
It remains above the protected 531-depth result; repeated affine phase
rebasing and lack of cross-term XAG sharing are the next bottlenecks. Details
are in `docs/PHASE_RETENTION_REPORT.md`.

The retention beam now separates true path cost `g` from heuristic `h`, and a
global term-6 `(live, emitted-mask)` search completed in 1,295 states at
204/188. Search diagnostics are recorded in
`artifacts/retention_search_diagnostics.json`.

## Hybrid portfolio and affine-frame assessment

The complete portfolio compiler in `src/rank_portfolio.py` tested the existing
pair, parallel-XAG, minMC, phase-pebble, and retention primitives on all ten
Pareto terms, then compiled 500 random term orders. The best complete oracle
was exhaustively verified at **840/798/18** (depth/CX/width). The affine-frame
model and staged cost breakdown are in `src/affine_frame.py`,
`src/phase_retention_affine.py`, and `artifacts/affine_frame_cost_breakdown.json`;
no affine improvement is claimed yet. Cross-term inventory found 42 unique x
and 40 unique y internal predicates with no duplicates. Full details are in
`docs/HYBRID_AFFINE_REPORT.md`.
The historical `xag_affine.qasm` diagnostic was rechecked and rejected for a
phase mismatch; it is not a valid candidate.
The shared formula-graph vector probe was also negative: 46 x and 45 y nodes,
versus 42 and 40 in the independent cached graphs.
The global ten-term phase-edge-sharing probe was also verified but scored
1591/1094 with 91 nonlinear nodes, so it does not improve the hybrid.

SDK login completed and native synthesis worked. These trials were real synthesis runs, not merely proposed code.

- `classiq_search.py`: high-level QNum bitmask/formula expressions produced excessive width (observed 67 or 153), unsuitable for 18-qubit constraint.
- `classiq_bits.py`: explicit QArray bit expressions synthesized at about depth 1651 / CX 1886. Better width behavior, insufficient depth.
- `classiq_lookup.py`: native `CArray` table indexed by a 6-bit QNum, 3-bit radius output, max-width 12. Synthesized lookup alone was depth 614 / CX 350, worse than custom lookup. Its one context Hadamard call was stripped before scoring.
- `nested_formula.qmod`, `nested_bits_formula.qmod`, `rank_whole.qmod`, and `lookup.qmod` are experimental models. **None is the companion QMOD for `full_mux.qasm`.**

## Mixed-variable 6-LUT decomposition (September 8, 2026; active branch)

The next architecture searches for
`logo(x,y) = G(h0(z_S0), ..., hk(z_Sk))`, where each feature is an arbitrary
Boolean function of at most six of the twelve coordinate bits. The fixed-
support feasibility checker is `src/lut_decomposition.py`; it uses Z3 with an
explicit upper truth table `G`, so each candidate support tuple is tested over
all 4096 inputs. `src/lut_mux_oracle.py` is the corresponding parallel-UCR
emitter for a future satisfying model.

`solve_joint_z3` in the same module is the arbitrary-support formulation: Z3
chooses six increasing bit positions for every feature and its 64-entry LUT
at the same time, with complete-domain counterexamples added incrementally.
Feature-support rows are lexicographically ordered to remove feature-
permutation symmetry, and candidate models are canonicalized under LUT output
complement/codebook symmetry before scoring. This is more faithful to the
intended search than sampling fixed supports, but significantly more expensive.
`solve_joint_z3_array` is an equivalent array-indexed encoding using
`Select(table, code)` rather than a 64-way selector expansion; it reduced the
runtime of the same 20-round probe from about 23/37 seconds to about 11/21
seconds for k=4/k=5. A deeper k=4 run reached `unknown` at round 16 with
4,030 pairs and no model. Both joint encodings also enforce the necessary
condition that all 12 essential input bits occur in the union of the supports.
A deeper k=5 CLI run reached `unknown` at round 15 with 3,780 pairs and no
model; this is likewise a solver performance result, not an infeasibility
claim.
Using a 25-pair refinement batch, a k=5 run reached 30 rounds and 760 pairs
in 8.5 seconds with no model. Extending the same run to 300 rounds reached
`unknown` only at round 109 with 2,735 pairs after 144 seconds; no model was
found. Smaller batches therefore improve progress, but have not yet produced
an exact decomposition.
A five-seed repeat of the 60-round, 25-pair-batch k=5 configuration reached
the round limit for every seed (1,510 pairs each), with no timeout and no
model. This is repeatability evidence, not a proof over the unsampled support
space.
`solve_joint_z3_bool` is a pure-Boolean one-hot support/LUT encoding. Its
300-round k=5 probe reached `unknown` at round 133 with 3,335 pairs and no
model, modestly deeper than the array encoding but still not convergent. It
now also enforces lexicographic order between feature-support rows; the same
seed/configuration after that symmetry break reached `unknown` at round 124
with 3,110 pairs and no model.
With a one-collision-per-round batch, pure-Boolean runs for both k=4 and k=5
completed all 1,000 rounds and 1,010 accumulated pairs without timeout or
model (about 172 seconds for k=4 and 209 seconds for k=5). These are the
deepest stable bounded runs; they still do not prove infeasibility over the
full support space.
Because the exhaustive ABC-family combinations used distinct support rows, an
additional 100 random five-row multisets (allowing repeated supports) were
checked with fixed-support CEGAR; all 100 were UNSAT with no timeout or model.
PySAT is installed and `solve_joint_pysat` provides the same one-hot CEGAR
encoding through an incremental native SAT solver, including lexicographic
feature-row symmetry breaking. Its corrected/vectorized k=5 run completed
2,000 one-collision rounds and 2,010 pairs without timeout or model in about
140 seconds. The CLI selects it with `--encoding pysat`.
`solve_joint_pysat_direct` also encodes all 4,096 inputs at once with explicit
G and six-level LUT mux trees. The resulting k=4 logo CNF had 1,198,062
variables and 5,219,037 clauses; a 1M-conflict decision remained unresolved
and was stopped, so it is not an UNSAT result. The same direct encoding passed
an exact synthetic parity regression and returned SAT with a verified model.
The corresponding k=5 direct CNF has 1,546,864 variables and 6,950,256
clauses; a bounded decision returned `unknown` without a model.
PySAT now also accepts a conflict budget and reports `unknown` cleanly. A
larger-batch k=5 run with 100 collisions per round returned `unknown` at round
46 with 4,620 pairs under a 5,000-conflict budget.
The PySAT encoding also passed an end-to-end synthetic regression: it recovered
an exact four-feature decomposition of a known 12-bit parity predicate, and
the returned supports/tables/G matched all 4,096 inputs. This validates the
support-selection, LUT, collision, and G reconstruction clauses independently
of the logo search.
As an out-of-scope diagnostic at the six-ancilla ceiling, a native-SAT k=6
run reached its 200-round limit with 5,010 pairs and no model. This does not
replace the required k=4/k=5 search, but indicates the difficulty is not
limited to the smaller feature counts.
The direct form is exposed with `--direct` in the search CLI.

Initial classical screening has not found a model yet:

- 25 structured/random four-feature support tuples returned UNSAT using the
  direct all-4096-input Z3 encoding.
- An additional 10 random four-feature tuples returned UNSAT under the
  incremental CEGAR encoding, with 20 rounds and up to 3 seconds per solver
  check. A previous 60-tuple bounded CEGAR screen produced 36 UNSAT results
  and 24 round-limit results; it found no model.
- Three structured five-feature tuples returned UNSAT using the direct
  encoding. A subsequent eight-tuple random five-feature CEGAR screen found
  six UNSAT results and two `unknown` timeouts; it found no model.
- Parsing the existing ABC map yields 13 distinct six-input supports. The
  reproducible driver `src/search_lut_supports.py` exhaustively tested all 715
  four-support combinations and all 1,287 five-support combinations from this
  family. Every one returned UNSAT; there were no `unknown` results and no
  model in either sweep.
- These are support-level results, not a proof that all four- or five-LUT
  decompositions are impossible. The `unknown` results and the unsampled
  support space remain pending.
- A separate 100-tuple random arbitrary-support five-LUT screen produced 75
  UNSAT results, 24 solver timeouts (`unknown`), and one CEGAR round limit; it
  found no model. This is additional screening evidence only.
- The first joint arbitrary-support trials reached `unknown` after three
  refinement rounds for k=4 (3,008 accumulated pairs) and four rounds for k=5
  (7,622 pairs), with no model. These are performance limits, not UNSAT
  results.
- With smaller 100-pair refinement batches, 20-round joint runs for both k=4
  and k=5 reached their round limit with 2,020 accumulated pairs and no model.
  This improved progress through the search but still did not establish
  infeasibility.
- An extended symmetry-broken k=4 run reached `unknown` at round 47 with 4,720
  accumulated pairs and no model. It remains a timeout/performance result.
- `src/lut_mux_oracle.py` now contains the exact parallel-UCR
  load/phase/unload emitter, but no satisfying model has yet been found, so
  no quantum logo candidate has been emitted from this branch.
- The independent ABC 6-LUT mapping of `experiments/logo.bench` reports 57
  mapped nodes over four levels. This is useful context for the search, but
  it is not an equivalence proof against the restricted independent-feature
  architecture and is not a QASM score.

The fixed-support sweep is reproducible with `src/search_lut_supports.py
--k 4` or `--k 5`; the unrestricted array-indexed search is exposed with
`--joint --k 4` or `--joint --k 5` and accepts the CEGAR batch/round/time
parameters.

## Second-iteration conclusion and architectural decision (September 8, 2026)

The mixed-support LUT work should be treated as a completed negative direction,
not as an invitation to run a larger generic Boolean-decomposition search. The
structured support family was exhausted without a model, while the unrestricted
Z3/PySAT formulations became computationally unresolved before producing a
quantum candidate. This is not a proof that no arbitrary LUT factorization
exists; it is strong enough evidence that extending the same SAT formulation is
poorly aligned with the optimization objective and should not be the primary
next step.

The current exported baseline was also inspected directly, rather than only
through `src/full_mux.py`. `artifacts/full_mux.qasm` is depth 536 with 1,020
CX gates. Counting every serialized QASM operation touching each clean ancilla
gives q15=403, q16=373, q17=337, q12=301, q13=261, and q14=236. Because
operations sharing one qubit cannot occupy the same circuit layer, the current
gate multiset has a per-qubit serialization lower bound of 403 layers. Thus a
depth near 291 cannot come from merely reordering this work or making small
compiler cancellations; it requires removing or replacing a substantial amount
of ancilla-mediated computation. This does not prove that a sufficiently
aggressive global rewrite could never remove enough gates, but it shows why
PyZX, pytket, Qiskit seed changes, or local gate ordering should be treated as
secondary cleanup experiments rather than the main route from 536 to the
leaderboard range.

Independent predicate checks point in the same direction:

- The signed global Walsh spectrum has all 4,096 coefficients nonzero.
- The Boolean ANF has 886 nonzero monomials and reaches degree 12.
- The 64x64 truth-mask rank is 10 over GF(2), but the existing rank approach
  already demonstrated that algebraic rank does not translate into a cheap
  reversible schedule.
- Row/column class compression is experimentally rejected: the best class
  artifact remained depth 4,079, and the transposed layout was worse.

The resulting decision is to stop treating direct Walsh/parity synthesis,
plain rank factorization, row/column class decoding, and generic independent
mixed-LUT decomposition as the primary directions. Future work should target a
new architecture that reduces the three large lookup/phase/uncompute stages or
shares their ancilla work more fundamentally. Global rewriting remains useful
only as a bounded follow-up after an architectural change, with exact U3/CX
serialization and exhaustive verification preserved.

## Structured five-input radius lookup (September 8, 2026; next architectural hypothesis)

Inspection of `src/radius.py` exposed a more targeted opportunity than a generic
Boolean decomposition. The top y bit, `y5`, separates the two nonzero disk
bands: the D2 rows occur in the lower `y5=0` band and the D1 rows in the upper
`y5=1` band. It is not by itself a complete disk-membership flag, because many
rows in each half have radius zero, but it is an exact family selector whenever
the disk radius is nonzero.

For any radius feature `h(y5,y0..y4)`, Shannon decomposition gives

`h = h0(y0..y4) XOR (y5 AND Delta_h(y0..y4))`,

where `Delta_h = h0 XOR h1`. Both `h0` and `Delta_h` are five-input Boolean
tables. A five-control uniformly controlled rotation has 32 table positions
instead of 64, so its Gray/UCR portion is expected to be about half the depth
of the current six-control implementation (roughly 64 rather than 128 layers
before selection and compiler effects).

For the three radius bits, six five-input tables can be loaded in parallel:
`h0,0`, `h0,1`, `h0,2` and `Delta_0`, `Delta_1`, `Delta_2`. The selected radius
could then be formed with three y5-controlled toggles. This is a concrete,
predicate-specific optimization hypothesis and has not appeared in the earlier
experiment history.

There is an important six-ancilla constraint. The six-table construction uses
three ancillas for the h0 bank and three for the Delta bank, while `full_mux`
normally needs all six clean ancillas simultaneously for `R0,R1,R2,A,B,V`.
The Delta bank must therefore be uncomputed before those wires are reused, or
the radius and left-shape feature groups must be scheduled sequentially. The
selection toggles also share `y5`, so their cost is small but not literally
zero-depth. A successful implementation must compare the added scheduling and
uncompute depth against the savings from the shorter UCRs, preserve arbitrary
input semantics, and exhaustively verify a new serialized QASM.

This is now the preferred next implementation experiment because it attacks the
dominant lookup architecture using known geometry, without assuming an
unverified global decomposition. The first prototype should target the radius
load/select/unload subcircuit in isolation, then test whether the saved ancilla
and stage structure can be integrated with the A/B/V left-shape lookup.

## Threshold radius encoding and comparator removal (September 8, 2026; strongest current hypothesis)

Merely replacing a six-control radius lookup by a five-input Shannon split would
save only one lookup's compute/uncompute cost, leaving an estimated depth near
408. The more important opportunity is to stop storing the radius as a binary
integer and remove the general-purpose reversible comparator that consumes it.

The radius values actually used by the disk construction are only
`{0,2,4,5,6,7}`; radius 8 is handled by the existing special correction. A
useful representation is:

| r | V=[r>0] | L=[r>=4] | T=[r>=6] | P=[r odd] |
|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | 0 |
| 2 | 1 | 0 | 0 | 0 |
| 4 | 1 | 1 | 0 | 0 |
| 5 | 1 | 1 | 0 | 1 |
| 6 | 1 | 1 | 1 | 0 |
| 7 | 1 | 1 | 1 | 1 |

After the existing x folding, classify the folded distance `d` by value. The
predicate `d <= r` can then be expressed using the threshold features:

- `d <= 2` uses `V`;
- `d in {3,4}` uses `L`;
- `d = 5` uses `T OR P`;
- `d = 6` uses `T`;
- `d = 7` uses `T AND P`.

This could replace the three-step Cuccaro-style binary comparator with a small
set of disjoint phase conditions over the folded-distance bits and `V,L,T,P`.
It is a much more targeted use of the geometry than computing and comparing an
arbitrary binary radius. The exact cost is still unknown: the five conditions
must be synthesized with valid dirty-workspace semantics, and their relative
phase/uncompute behavior must be checked. Removing the comparator does not
remove the folding, equality guard, radius-eight correction, or all associated
phase-control cost.

There is also an exact output redundancy. Direct evaluation of `src/radius.py`
confirms that the bar flag satisfies `B = y5 AND T` for all 64 y values. The
current six loaded features `R0,R1,R2,A,B,V` therefore need not remain six
independent stored variables. A future representation could load `A,V,L,T,P`
and form the bar condition transiently from `y5` and `T`, potentially freeing a
clean wire for selection or phase workspace. Likewise, `V` is the OR of the
binary radius bits, although recomputing that OR is not automatically cheaper
than loading `V` directly.

The design principle is to optimize the representation for the consuming phase
operations, not for semantic neatness. This threshold encoding, combined with
the five-input y5 split, is the strongest current architectural experiment.
The first prototype should compare complete serialized U3/CX depth and CX
count against `full_mux`, not just the abstract deletion of the comparator.

## BDD structure (September 8, 2026; analysis, not yet a circuit)

An exhaustive ordinary-variable-order search found a surprisingly small reduced
ordered binary decision diagram for the complete 12-bit predicate. The reported
order is

`x0,x1,x5,x2,x3,x4,y5,y4,y3,y2,y0,y1`

with approximately 91 nonterminal cofactor states. The level widths were
reported as approximately `2,4,7,11,15,10,11,14,10,4,2`, which indicates
substantial classical sharing under this order. This is a useful new structural
signal: the predicate has a compact decision representation even though its
Walsh spectrum and ANF are dense.

The result does not directly imply a compact reversible oracle. A straightforward
reversible OBDD must retain enough live branch/cofactor information to uncompute
the path, and the tested realizations exceeded the six clean-ancilla workspace.
Random variable-order searches did not find a naive reversible OBDD that fits
the workspace. No QASM, exhaustive-verification report, or checked-in BDD
generator is currently associated with this result, so the state count and
widths should be treated as an analysis finding rather than a verified circuit
milestone.

The correct follow-up is selective extraction, not full OBDD materialization:
look for a few high-sharing BDD cofactors or threshold predicates that can be
computed into existing ancillas and reused across the lookup/phase/uncompute
stages. BDDs should therefore remain a source of candidate shared intermediates,
but not the next primary implementation architecture.

### Cofactor inventory (September 9, 2026)

`src/bdd_cofactor_mine.py` reconstructs the exact target truth table under the
documented order and enumerates the reachable reduced-BDD nodes. It found 109
reachable nonterminal nodes and 109 distinct nonconstant cofactor functions,
matching the previously reported approximately-91 state count only up to the
different node-count convention used by the analysis. The inventory is saved
at `artifacts/bdd_cofactor_inventory.json` with each node's exact 4096-point
truth mask, support, and population.

This is an analysis milestone, not a circuit result. The next implementation
should select a small set of these masks with shared support and test whether
they can replace repeated feature loads under six clean ancillas. The node
inventory itself does not justify a depth claim.

`src/bdd_cofactor_score.py` then scored 64 cofactors with support size at most
six using exact compute/phase/uncompute circuits. The cheapest nontrivial
cofactors cost 11 depth / 5 CX, while the most complex six-input cofactors
cost 216 depth / 137 CX. This confirms that the BDD exposes cheap local
predicates, but it does not yet show that their phase contributions can be
shared globally; no full-oracle QASM was generated or accepted.

`src/bdd_reversible.py` tested the direct Shannon recurrence
`f = lo XOR (variable AND (lo XOR hi))` with exact Toffolis and five scratch
ancillas beside the output ancilla. It exhausted the six-clean-ancilla budget
before reaching the root, so no QASM was emitted. This closes the naive direct
BDD evaluator; a viable BDD route would need dirty-input pebbling or a more
aggressive multi-output schedule.

`src/bdd_dirty_reversible.py` implemented the corrected dirty-target sequence
(`aux ^= delta`, controlled use, uncompute, correction controlled use). It fit
within width 18 but produced depth **3,949,563** and **2,581,968 CX**. This is
decisively negative; the candidate is retained as a diagnostic and was not
exhaustively verified.

## Side-separated minimum-MC rank compiler (September 9, 2026)

The requested experiment began with `src/rank_factor_inventory.py`. It restored
the supplied `rank_mc_pareto_terms.json` only after exact reconstruction of the
64x64 target, and produced `artifacts/rank_factor_inventory.json` containing 30
deduplicated scalar functions across `pair_terms`, `rank_terms`, and the Pareto
rank basis.

`src/parallel_rank_pair.py` tested the existing formula backend with separate
three-wire x/y banks. It fit only a small minority of factor-side computations;
most required more than two scratch wires, so it cannot compile a ten-term
rank oracle.

`src/parallel_rank_pair_xag.py` then used the repository XAG graph and a strict
three-live-node reversible pebbling schedule, pinning one root node to the
side's output wire. The surviving pairs demonstrate real side parallelism:
for example, a Pareto pair measured 50 pair depth / 65 CX after U3/CX
serialization, and an independent sparse simulation checked all 4096 basis
inputs with exact input preservation, zero ancilla leakage, and global phase 1.
But the backend could produce valid three-slot pairs for only 2/10 `pair_terms`,
1/10 `rank_terms`, and 2/10 Pareto terms. Therefore the strict local compiler
fails the full-factor prerequisite and the full rank oracle was not attempted.
The binding issue is not x/y parallelism; it is the lack of a genuine
minimum-MC representation and reversible schedule that fits one output plus
two scratch wires for the difficult six-variable factors. Metrics are in
`artifacts/parallel_rank_pair_xag_metrics.json`.

## Ideas considered but not implemented or validated

- PyZX/pytket global simplification of compute/phase/uncompute: packages installed; optional bounded diagnostic after an architectural change, not the primary search direction.
- Fold/translate y before lookup to lower control count: likely savings compete with constant adders, region guards, and exceptional rows. No tested win.
- Encode row classes and column thresholds into three ancillas each, then compare: possible parallel lookups, unresolved guard complexity.
- Align disks with a conditional high-x transformation involving y5*x5 while preserving left shapes: only a hypothesis.
- Alternative radius flags V, L=(r>=4), T=(r>=6), P=odd. Then r>=5 is T OR P, r>=7 is T AND P; for the current table, bar-y flag equals y5 AND T. Could reduce lookup duplication but needs a new reversible phase/comparator design.
- More control-order seed search alone is unlikely to bridge the remaining 245 depth to the observed leader.

## Five-input Shannon split prototype (September 8, 2026; verified negative)

`src/shell_mux.py` implements the first concrete shell-architecture test. It
uses `h=h0 XOR (y5 AND (h0 XOR h1))` for each radius bit, loads the three
`h0` values into q12..q14, loads deltas into q15..q17, selects with Toffolis,
and clears the delta bank before reusing it for A/B/V. All transpilation uses
`qubits_initially_zero=False`.

The initial CNOT-only selection was invalid and is retained as
`artifacts/shell_mux_candidate0.qasm`; it failed with phase error 2. The
corrected `artifacts/shell_mux_candidate1.qasm` passed exhaustive verification:
depth 969, CX 1244, width 18, SHA
`6c5a35313c2f26509426fde8bbf6195fb61da742cf86576f7677fbc0c699dfa4`.
Seeds 1..7 measured depths 949, 965, 957, 965, 961, 969, 959. This simple
split is therefore closed as a negative direction; the next useful experiment
is a threshold-shell phase that removes the binary comparator.

## Comparator-free threshold shell prototype (September 8, 2026; verified negative)

`src/threshold_shell.py` implemented the next experiment rather than merely
shortening the radius loader. It loaded `V,L,T,P,E`, folded x, emitted the
distance-shell phase conditions, integrated the D2 radius-eight case, unloaded
the threshold features, and then applied the left-shape phase using direct
`A XOR V` and `B XOR V` tables. The binary radius comparator and separate
radius-eight correction were removed from this candidate.

The serialized candidate passed exhaustive verification on all 4096 inputs with
zero ancilla leakage:

| Artifact | Depth | CX | Width | SHA |
|---|---:|---:|---:|---|
| `artifacts/threshold_shell_candidate1.qasm` | 4437 | 3854 | 18 | `4eb6fc7fe03909714c8f135bc3512e260768c6ffdf8a8decc69282d810f3b7e6` |

This is a strong negative result for the naive implementation, not for the
threshold idea itself. The prototype replaced one shared arithmetic comparator
with dozens of separately synthesized high-control phase cubes. The comparator
cost disappeared, but the unshared shell phase network became dramatically
more expensive. The operation-specific representation therefore needs a shared
shell/UCR construction or a reusable folded-distance predicate; direct
enumeration of threshold-conditioned phase cubes is closed as a route to the
target.

## Verification tools

`exhaustive_verify.py` parses the saved QASM and sparsely simulates every clean-ancilla basis input together. It tracks coordinate mapping, diagonal phase, ancilla leakage, and a numerical discarded-amplitude bound. It aborts if sparse support exceeds 2048; a more mixing optimizer may require a blocked dense verifier instead. The current best peaks at support 64.

`verify.py` uses Qiskit Aer on random dense complex superpositions over all coordinates, compares the full output including ancillas, and maintains a shared global phase across tests. This is an independent simulation path, but probabilistic. It has now also passed on the current 536-depth best with five random dense states.

A phase-only truth-table check that ignores relative phases or dirty ancillas is insufficient. Always verify the exact exported standalone circuit, not just its high-level Boolean formula or its behavior on a uniform input.

## Session of September 8, 2026 (second continuation): bilinear-rank analysis

### New structural facts about the target function

Let `F[y][x] = logo(x,y)`.

- `F` has exactly **11 distinct rows** and **11 distinct columns**, and its
  **GF(2) rank is 10**. Script: analysis reproduced by transforming `MASK` in
  `src/search.py`; the rank is computed by GF(2) elimination over the 64 row
  vectors.
- A rank-10 bilinear decomposition is explicit and geometric:
  `f = sum_k u_k(x) v_k(y)` with the `v_k` the nested y-intervals
  `G1..G5 = [17,21],[15,23],[13,25],[12,26],[11,27]` (D2 thermometer),
  `H1..H4 = [39,43],[37,45],[36,46],[35,47]` (D1 thermometer) and
  `K = [29,53]` (square rows); the `u_k` are the matching x annuli.
- The 12-variable ANF of `f` has 886 terms (degrees 2..12), so direct
  multi-controlled-Z expansion is hopeless.
- **No Walsh coefficient of the phase function can ever be cancelled.** For a
  parity phase term `S`, `4096 * f_hat(S) = sum_z f(z) chi_S(z)`, which is
  congruent mod 2 to `|f| = 1097`, an odd number. Adding any integer multiple of
  `2*pi` changes the coefficient by an even amount, so every one of the 4096
  coefficients stays nonzero. An ancilla-free phase-polynomial oracle therefore
  needs all 4096 parity terms; ancillas are mathematically required, not merely
  convenient.

### Why 6 clean ancillas are enough in principle

A "load y features / phase from x / unload" round with `m` ancillas realises
phase terms that are **linear in the ancillas**, hence rank at most `m`. Rank 10
with 6 ancillas looks impossible, but a y-conditioned reversible transform of
the x register doubles the reachable rank to `2m = 12`, because each stored bit
then carries one x function per band.

Such a transform exists and is cheap. Let `tau` flip `x0..x4` when
`x5 AND y5`. On `x5 = 1` it is the reflection `x -> 95 - x`, which maps the D1
centre 55 onto the D2 centre 40, so both disks share one centre and one annulus
family; on `x5 = 0` it is the identity, so the square's x range `[2,26]` is
pointwise fixed and the square term needs no band split.

### `src/shell6.py` — comparator-free six-shell oracle (verified negative result)

Ancillas hold six y features, all unions of two intervals:

| wire | y feature | x table applied in reflected coordinates |
|---|---|---|
| 12 | `[11,27] u [35,47]` | `[38,42]` |
| 13 | `[12,26] u [36,46]` | `{36,37,43,44}` |
| 14 | `[13,25] u [37,45]` | `{35,45}` |
| 15 | `[13,25] u [39,43]` | `{34,46}` |
| 16 | `[29,53]` | `[2,26]` |
| 17 | `[39,43]` | `[27,31] u [47,63]` (bar image) |

The classical identity was checked over all 4096 points with zero mismatches
before any circuit was built. The six x tables partition every x except
`{0,1,32,33}` (exactly the states with `x1=x2=x3=x4=0`); the missing `-i` factor
from `RZ(pi)` is restored by one negated-control `MCP(-pi/2)`, so the leftover
phase stays global. The radius-7 and radius-8 shells do not fit into six
ancillas and are supplied by two `pair_circuit` terms,
`{33,47} x [15,23]` and `{32,48} x [17,21]`.

Measured, per stage: lookup 128 depth / 342 CX, phase 128 / 302, `tau` 27 each
way, `MCP` fix 33, corrections 97 and 71. Best over seeds 0..3 was
**depth 615, CX 1182, width 18** (`artifacts/shell6.qasm`, seed 0). It passed
exhaustive verification on all 4096 inputs with zero ancilla leakage, maximum
error 1.63e-14, SHA
`2392f057a77fec8441e24366e8805f54ad8d700213536c41ecdf1bb041cc1517`
(`artifacts/shell6.exhaustive.json`), so the decomposition is confirmed correct.
It is, however,
worse than the depth-536 `full_mux` baseline: removing the Cuccaro comparator
saves less than the two pair corrections plus `tau` cost. The architecture is
recorded because it is comparator-free and is the natural host for a cheaper
loading primitive, not because it is competitive as built.

### The 384-layer barrier (the main conclusion)

Every architecture in this family pays `3 x 128` layers: load, phase, unload.
The 128 is not an artefact of the current code.

- A UCR over 6 controls puts 64 rotations and 64 CNOTs on one target wire, so
  that wire has 128 operations and the stage cannot be shallower, however many
  outputs run in parallel.
- Skipping zero Walsh angles cannot help, because the stage depth is the maximum
  over its outputs. In the `full_mux` load, the Walsh supports are
  `R0 = 64, R1 = 47, R2 = 40, A = 64, B = 64, V = 40`; in the phase stage
  `S = 64, Bx = 40, O = 64`.
- Re-basing does not help either. Ancilla features may be replaced by any
  invertible GF(2) combination (a depth-few CNOT network converts back), but a
  greedy search over all 63 combinations of `R0,R1,R2,A,B,V` shows the
  combinations with Walsh support below 64 span only a 5-dimensional subspace,
  so **every basis contains at least one Walsh-dense feature**. The same search
  over the `shell6` features leaves the maximum at 64.
- Classical loading is not cheaper here. A shared XAG for the six `full_mux`
  features needs 44 AND nodes (45 for the `shell6` features); at roughly 6
  layers per relative-phase Toffoli and the limited parallelism available with
  no spare scratch, that is about 130 layers, i.e. no better than the UCR, which
  is consistent with the earlier XAG attempts.

Load plus unload alone is about 684 CX, which already exceeds the leader's
reported 655 CX. Together with the 384-layer floor this is strong evidence that
**the sub-300 leaders are not using 6-control uniformly controlled rotations at
all.** Any further work in this workspace should target that primitive rather
than the surrounding structure.

### Global rewriting: bounded diagnostic completed

pytket 2.18.1 was applied to `artifacts/full_mux.qasm` and rebased to exact
`u3`/`cx`. `FullPeepholeOptimise` and `CliffordSimp` both give depth 531 with CX
unchanged at 1020; `KAKDecomposition` gives 536. This closes the open question
in `CURRENT_DESIGN.md`: global rewriting recovers about 1 percent and cannot
approach the leader range, exactly as the 403-layer per-qubit serialisation
bound predicted.

### Bounded exact min-MC XAG probe: verified negative gate result

`src/minmc_xag.py` searched exact six-variable XOR-AND representations with
Z3, testing 0 through 6 AND nodes and allowing arbitrary affine inputs at
each node and at the output. Of 30 deduplicated rank-factor functions,
29 models were returned and independently verified by integer truth-table
evaluation; one timed out within the configured bounded search. The cache is
`artifacts/minmc_factor_cache.json`.

`src/minmc_rank_pair.py` mapped those models into the existing explicit
three-live-value reversible pebble schedule, with disjoint x/y banks and
`qubits_initially_zero=False` in every transpilation. Only one complete
Pareto pair survived cleanup: 139 depth / 215 CX / width 18. Most models
were not pebbleable with one output plus two scratch wires, and the unresolved
factor prevented one pair. This does not beat the protected 531/1020 best and
does not justify constructing a ten-term oracle. It establishes that minimum
AND count without a reversible-cost or pebbling objective is the wrong
optimization target for this architecture.

`src/pebble_xag.py` was then used as a narrower follow-up. It synthesizes
chain-shaped XAGs where each AND node depends only on the six inputs and the
previous AND node, which is favorable to reversible recomputation. It solved
29/30 factors, but `src/minmc_rank_pair.py` compiled only 5/10 complete pairs
per basis. The partial pair-depth sums were 771, 744, and 793 for
`pair_terms`, `rank_terms`, and `rank_mc_pareto_terms`, respectively, before
missing terms were included. The chain restriction therefore does not provide
a route below the protected 531-depth oracle.

`src/gl10_actual_search.py` then performed an 80-step GL(10,2) transvection
search from each known ten-term basis, compiling and serializing each
candidate before scoring it. Best results were 779/736 for `pair_terms`,
795/754 for `rank_terms`, and 803/751 for `rank_mc_pareto_terms`; no candidate
improved the trusted 779-depth pair baseline.

### Dirty-input ESOP pair compiler: verified negative result

`src/dirty_esop_pair.py` tested the remaining dirty-workspace idea by
computing each six-variable ESOP directly into q12 and q13 with relative-phase
MCX blocks, applying CZ, and composing the exact inverse compute sequence.
The resulting standalone `artifacts/dirty_esop_pair.qasm` passed all 4096
basis inputs with zero ancilla leakage, but measured **2156 depth / 1346 CX /
width 18**, so MCX cost dominates and the approach is closed.

### Exact Walsh phase polynomial with GraySynth: verified negative diagnostic

`src/phase_polynomial_aam.py` generated the exact Walsh expansion of the
12-variable Boolean phase and synthesized its 4095 nonconstant parity terms
with Qiskit's GraySynth implementation. The odd 1097-pixel parity result
indeed produces all **4096** nonzero Walsh coefficients. The ancilla-free
diagnostic measured **8168 depth / 4094 CX / width 12**, confirming that
parity-network synthesis does not remove the phase-complexity bottleneck.

A bounded sweep of all supported GraySynth section sizes (`1, 2, 3, 4, 6,
12`) gave the same **8168 depth / 4094 CX** after exact U3/CX serialization;
the measurements are in `artifacts/phase_polynomial_aam_sections.json`.

### QROM-tree radius lookup: verified negative result

The previously unbenchmarked `src/qrom_tree.py` was run as a complete
radius-based oracle. Its isolated lookup measured 171 depth / 106 CX, but the
complete `artifacts/radius_tree.qasm` measured **777 depth / 606 CX / width
18**. Exhaustive verification checked all 4096 basis inputs, with zero
ancilla leakage and SHA
`9a0d5a2a6d2869ae82030cb50671efc3bb7faeb6641a29dcb524e1721a09cfd8`. The
tree lookup is correct, but its surrounding radius/comparison and phase
work dominate; the lookup-only number is not an oracle score.

An attempted mixed feature schedule used the already-live `A` indicator as a
dirty scratch wire while computing `V` with the ordinary clean-target
`smart_compute` recursion. It was rejected immediately: exhaustive testing
of the 64 y states produced a wrong `V` value at `y=35`. Ordinary reversible
recursion cannot treat a live predicate as a clean scratch target; a valid
dirty-ancilla route needs a dedicated dirty-target identity.

### Hybrid direct-A load: verified negative depth result

`src/hybrid_a_mux.py` replaced only the simple square-row feature `A` with a
formula-based compute into q15, using q16 plus q12..q14 as temporary clean
workspace and restoring it before the radius lookup. The other features and
the phase identity remained unchanged. Across eight seeds, the best
`artifacts/hybrid_a_mux.qasm` measured **643 depth / 981 CX / width 18** and
passed all 4096 basis inputs with zero ancilla leakage (SHA
`12782997ceaafc2dd4f4bc7aa375dac0f8dbff3b1d5779acf3716267c9eddc2f`). The
lower CX count does not compensate for the added depth, so this hybrid is not
a submission improvement.

The stronger two-feature variant `src/hybrid_ab_mux.py` directly computed both
`A` and `B` with clean scratch before loading only `R0..R2,V` by UCR. It also
passed all 4096 basis inputs, but its best of eight seeds measured **737 depth
/ 913 CX / width 18**, SHA
`ca7c59ea8d99503a28e64cee5a0a6f86b89e1755184fe73d74ea339b853a9b74`. Direct
compute/uncompute and the changed ancilla critical path outweighed the two
removed loads; simple-feature replacement is therefore closed.

The same bounded test was run for the simple bar feature `B`: direct
reversible computation of `B(y)` into q16, followed by the existing UCR load
for `R0,R1,R2,A,V`, was exact but measured **634 depth / 968 CX / 18 qubits**.
The serialized candidate is `artifacts/hybrid_b_mux.qasm`, with matching
exhaustive report and SHA `a9be69b2cdf4172a547982108e94a26d28520a0cccb88130e20dd9d341877331`.
It passed all 4096 inputs with zero ancilla leakage, but is far above 524;
replacing one simple feature independently is therefore closed as a useful
lever.

### Berkeley ABC AIG diagnostic: negative classical lower-level route

The built `experiments/abc/abc` binary was run on the exact 12-input logo
benchmark. Its `dc2` flow reached 224 AND nodes at level 22; the balanced
rewrite/refactor flow remained at 247 nodes and level 17, and `syn2` remained
at 247 nodes and level 19. These are classical AIG measurements, not quantum
scores, but they show that ABC does not expose a compact hidden computation
graph suitable for the six-clean-ancilla reversible compiler.

### Rank-2 rectangle basis follow-up

A bounded GL(2,2) search over the rank-2 rectangle union found the equivalent
representation `A_x*(A_y XOR B_y) XOR (A_x XOR B_x)*B_y`. The rectangle block
measured 277/236 depth/CX and the complete verified oracle measured
**659/727/18**, SHA
`34b34ef926b5e7ff2748334033801a1c569f1a6009bbe31b9ebb86a8583f7007`.
This supersedes 708 as the best disjoint-geometry candidate, but remains
above the protected 531 result.

Safe post-processing of that genuinely new candidate reached a verified
**649/727/18** using pytket `CliffordSimp` followed by Qiskit U3/CX lowering.
The exact artifact is `artifacts/disjoint_postprocessed_649.qasm`, SHA
`d752c2972c16210417ef683e8ce2a5afd4501df2158829592e31dbd7911f1265`.
Other bounded cleanup passes did not beat 649.

A shared five-output y-loader diagnostic was also attempted. Its initial
525-depth measurement was invalid because the live-feature RZ phase retained
an x-dependent zero-branch phase; it was discarded before artifact creation.
Adding the original parity-reference cancellation restored correctness but
measured 541/913 after a bounded loader/phase seed sweep, with bounded cleanup
at 536/947. Independent loader/phase and routing-seed trials found no lower
depth, so it does not beat the protected 531 circuit.

The separate-disk five-input lookup alternative was also checked. Two guarded
blocks produced an exact C XOR D oracle at **482/562/18**, SHA
`ce807f224c92be7e46825d107c48af78c518c9a574a21b6b250851659894dd30`.
It is worse than the shared 385/491 disk block and is closed.

## Joint five-output y-feature loader (September 9, 2026)

The new reversible-loading experiment began with the exact vector function
`y -> (R0,R1,R2,A,B)`. Its 64-row truth table has 10 distinct output
codewords, 36 unique ANF monomials, and 14 monomials shared by at least two
outputs. Three ABC multi-output flows produced a best natural-basis network of
56 AND nodes at logic depth 8. An affine output-basis screen scored 8,192
encodings and compiled 64 of them through ABC; after correcting the matrix
generator to guarantee invertibility, its best result was **46 AND nodes at
logic depth 7**. The y-input basis search below remains better on the depth
proxy at 48/6.

The exact minterm reversible reference was serialized and scored at **7463
depth / 3822 CX / width 18**. It is loader-only and intentionally not a
complete oracle. This confirms that the cross-output sharing must be converted
through a reversible pebbling schedule; the ANF/ABC results alone do not
justify integration. The complete 531-depth artifact remains unchanged.

The ABC networks were then parsed into affine-plus-AND graphs and screened
with the existing bounded clean-pebble planner. Across all 64 screened affine
output bases, **zero** bases allowed all five outputs to fit with five or fewer
live product nodes, which is the maximum available after reserving one clean
output accumulator. In the natural basis, even `A` requires six live pebbles;
the remaining outputs did not close under the bounded six-pebble search. This
is a feasibility result for the naive schedule, not an impossibility proof for
dirty-output or output-frame synthesis. Details are in
`artifacts/vector_feature_reversible_schedule.json`.

An optimistic dirty-frame span probe then allowed all six ancilla wires to
carry Boolean frame values and searched shared-node toggles. Its best bounded
state covered only 3/5 feature outputs after 12 abstract toggles. Because the
control-span restriction was relaxed, this is not a circuit or correctness
result; it only indicates that a simple final linear frame is not immediately
exposed by the natural ABC graph. The diagnostic is in
`artifacts/vector_dirty_frame_search.json`.

The local-coordinate fallback was then implemented. It translates low5 y by
19 in the lower half and 9 in the upper half, modulo 32, preserving y5. The
64-input mapping check passed. With three clean v-chain scratch ancillas, the
exact U3/CX transform measured **274/151/18**; the no-ancilla version was
425/247/18. Since the transform must be inverted, its pair is already about
548 depth before disk radius logic, so this fallback is closed.

The shared vector-ESOP fallback was then implemented using the 36 unique ANF
monomials and output masks. Its raw construction passed an independent 64-row
classical replay with q17 restored to zero. After exact U3/CX serialization it
measured **2505/1453/18** as a loader-only circuit. A prior 1354/840 result
was rejected because q15/q16, which are output wires, had been used as if they
were clean scratch. The corrected ESOP loader is therefore closed and was not
integrated into the complete oracle.

An affine basis search over the six y input bits then found a materially
better irreversible representation: 48 ABC AND nodes at level 6, versus
56/8 in the natural basis. The best map used rows `(1,2,4,40,16,48)` and
offset 16. Its exact input-basis shared-ESOP loader passed all 64 input
replays and measured **1973/1136/18**, improving 2505/1453 but remaining far
above the protected complete oracle. The input-basis loader was not integrated.

## Relative-phase dirty-output loader (September 9, 2026)

The next test replaced the no-ancilla MCX gates in the 26-monomial
input-basis loader with exact dirty-ancilla synthesis, temporarily using the
five output wires and restoring them. The ordinary exact dirty construction
measured **1996/1130/18** and was worse than the clean-output reference
1973/1136/18. A Qiskit three-control wrapper was avoided because its installed
version exposes a malformed four-qubit definition for a five-qubit dirty
gate; the direct synthesis API was used instead.

Allowing relative phase inside each compute/fanout/uncompute sandwich was a
much better loader primitive. The candidate
`artifacts/vector_input_basis_dirty_rp_loader.qasm` measured **1560/874/18**.
An independent statevector check of all 64 y inputs found one output basis
state per input, exact feature bits, restored y and q17, and one shared global
phase. This is still loader-only: it has not been composed with the x-phase
oracle, and therefore is not a complete challenge score. The protected
complete oracle remains `artifacts/531/full_mux_531.qasm` at 531/1020/18.

## Direct output-accumulator loader (September 9, 2026)

A more direct reversible schedule was tested after the dirty q17 loader. Each
shared ANF cube toggles its feature output wires directly; the other output
wires are restored dirty ancillas for the target MCX. This removes the q17
compute/fanout/uncompute sandwich. The exact serialized candidate
`artifacts/vector_input_basis_direct_target_loader.qasm` measures
**1478/823/18**, better than the 1560/874 relative-phase loader.

All 64 y inputs map to exact feature bits, restore y and q17, and pass the
independent statevector check. The four observed relative-phase classes are
intentional: this primitive is valid for a complete loader/inverse sandwich,
not as a standalone phase oracle. It remains loader-only and has not been
integrated into the protected 531 architecture.

Composing the serialized loader with its exact inverse and transpiling the pair
reduced to identity (depth 0 / CX 0), confirming cancellation of the internal
relative phases in the intended sandwich.

The required complete-oracle integration was then run in
`src/vector_loader_oracle.py`, replacing the six-output UCR load with the
direct five-output loader, deriving `V = R1 OR R2`, and retaining the original
phase/correction logic. Eight routing seeds were tested; the best exact
candidate was **3243/1965/18**, exhaustively verified on all 4096 inputs.
The large regression shows that a loader-only score is not predictive here:
the direct MCX schedule serializes heavily through dirty output targets and
does not belong in the complete architecture.

## Persistent output-frame loader (September 9, 2026)

The output-frame scheduler from the research brief was implemented. It keeps
`f = M p` for the five feature outputs, changes the invertible frame between
cubes, and selects frames so each nonlinear cube toggles one physical target.
The deterministic 2,000-sample-per-cube scheduler produced
`artifacts/vector_output_frame_loader.qasm` at **871/553/18**, with all 64 y
inputs verified and four internal relative-phase classes.

Replacing the direct loader in the complete integration with this frame loader
reduced the exact candidate to **2032/1425/18** across eight routing seeds;
seed 1 was best and all 4096 inputs passed exhaustive verification. This is a
substantial structural improvement over the 3243/1965 direct-target
integration, but remains negative against the protected 531 oracle.

## Derive V instead of loading a sixth UCR (September 9, 2026)

The brief's high-value `V = R1 OR R2` suggestion was tested directly in the
original architecture. The six-output y lookup was replaced by a five-output
lookup for `R0,R1,R2,A,B`, followed by an exact reversible OR into q17. Across
32 routing seeds the best complete candidate was **545/945/18** and passed
exhaustive verification. Safe pytket peephole lowering reduced that same
candidate to **540/945/18**, SHA
`4baad4c76a20db8e92ea7e2f2f68a0d8d9041e570d33275903bf38e3c228e39b` at
`artifacts/full_mux_derive_v_tket.qasm`; the optimized file also passed all
4096-input exhaustive verification. It remains worse than the protected
531/1020/18.

An additional 4,096-pair independent routing search (separate y and x seeds)
found raw 542/921 and pytket **537/921**, with all 4096 inputs verified. The
matching artifact is `artifacts/full_mux_derive_v_independent_best_tket.qasm`,
SHA `5b1878c951599e594ef404d219c46f4a1fdd412ee50a516d6c16ff53e5f44146`.
This closes the cheap routing-search opportunity while confirming a strong CX
near-miss.

## Relative-phase V derivation (September 9, 2026)

The reversible `V = R1 OR R2` step was then tested with relative-phase
Toffolis in the five-output architecture. A 1,024-pair independent routing
screen found raw **540/918** and pytket **535/918** at
`artifacts/full_mux_derive_v_rp_or_best_tket.qasm`. The candidate passed all
4096-input exhaustive verification; SHA
`a7ef23f038c2f4f1b6309899025283b32656d17fcd142f21618c9aeb013769f2`.
It is CX-efficient but remains four depth layers above the protected 531.

## Feature-to-ancilla assignment search (September 9, 2026)

The six logical y features in the full-mux skeleton were remapped over all
720 permutations of physical wires q12..q17. The comparator and phase cube
were remapped semantically as well: the third radius output remains the
carry/phase target, and V remains the phase-control feature. Every candidate
used `qubits_initially_zero=False`, optimization level 3, seed 94, and the
same downstream construction as the protected 531 circuit.

The best serialized candidate is `artifacts/530/full_mux_feature_permuted_530.qasm`:

| candidate | depth | CX | width |
|---|---:|---:|---:|
| protected 531 | 531 | 1020 | 18 |
| feature permutation | **530** | **1020** | **18** |

The winning assignment is `R0->q12, R1->q15, R2->q14, A->q16, B->q17,
V->q13`. The exact QASM SHA-256 is
`7f9676b2d372d9ca5eb31889bf9f3af1d6fc4a678bd9b782f6e67ef707938156`.
Exhaustive verification checked all 4096 clean-ancilla basis inputs, with
maximum error `1.52e-14` and zero ancilla leakage. Five dense random-state
checks also passed. Search metadata and metrics are in
`artifacts/530/feature_permutation_search.json` and
`artifacts/530/feature_permutation_metrics.json`.

This is a genuine one-layer improvement but remains far above the current
leaderboard range. The reproducible search is
`src/feature_ancilla_permutation.py`.

The follow-up independent-routing screen tested 2,048 combinations over the
eight strongest assignments, with separate y-loader, x-phase, and transpiler
seeds. It did not improve 530; its best was 530/1022. A six-order radius
comparator schedule screen also found no improvement over 530/1020.

Applying the same semantic feature-wire permutation search to the
five-output `V = R1 OR R2` architecture tested all 120 assignments with its
best known y/x routing seeds. The best candidate was **539/918/18**, and it
passed exhaustive verification; it remains worse than the 530 full-mux
candidate. This branch is closed.

## Affine six-feature loader encoding (September 10, 2026)

The six loaded features `(R0,R1,R2,A,B,V)` were jointly changed by an
invertible GF(2) output encoding before the y multiplexer. The circuit decodes
the features before the existing left-phase/comparator logic and reverses that
decode before applying the inverse loader. This preserves the original
compute/phase/uncompute semantics; the encoded loader is not treated as an
independent oracle.

The best bounded screen used matrix rows `(1,6,2,8,16,32)`, i.e. one shear
between the first two radius features, with the established physical feature
assignment `R0->q12, R1->q15, R2->q14, A->q16, B->q17, V->q13`. The exact
serialized candidate is:

| candidate | depth | CX | width |
|---|---:|---:|---:|
| previous verified best | 530 | 1020 | 18 |
| affine six-feature encoding | **529** | 1036 | **18** |

`artifacts/529/full_mux_feature_linear_529.qasm` passed exhaustive checking of
all 4096 clean-ancilla basis inputs: maximum error `1.59e-14`, zero ancilla
leakage, and matching SHA-256
`9d07529b678b046085fa5c0a32b4774e04cb6ba3650e779e4200609e133bc477`.
Five dense full-support checks also passed with maximum error `6.38e-16`.
The logical companion is
`artifacts/529/full_mux_feature_linear_529.qmod`; as with the earlier QMODs,
it describes the logical oracle and is not a gate-for-gate serialization of
the optimized QASM.

This is a genuine local improvement in the primary challenge metric, but it
is still far from the observed leaderboard range. The source is
`src/feature_linear_encoding.py`. The extra CX cost is accepted because depth
is the challenge's primary ranking field.

An additional bounded schedule test removed the multiplexer implementation's
cyclic-order restriction. It evaluated 101 complete candidates using arbitrary
independent permutations of the six controls for every y-loader output and
every x-phase output, while preserving the winning feature-to-ancilla mapping.
The seed-94 schedule reproduced **530/1020/18**; none of the 100 arbitrary
schedule candidates improved it. This closes control-order scheduling as a
standalone lever: the remaining gap requires a different loading/phase
primitive, not a rearrangement of the same UCR gate multiset.

## Final fallback checks: local-coordinate and BDD routes (September 9, 2026)

The local-coordinate fallback was revisited with relative-phase multi-controlled
flips. The transform still maps the low five y bits to the center-relative
coordinate, preserves y5, and passed the 64-input classical mapping check.
However, the exact serialized U3/CX score was **302 depth / 181 CX / 18
qubits**, worse than the existing exact transform at **274 / 151 / 18**. Since
the transform must be inverted around the phase operation, neither version can
be competitive before radius logic is added; this branch remains closed.

The direct dirty-workspace BDD evaluator was also run against the documented
109-node order. It produced **3,949,563 depth / 2,581,968 CX / 18 qubits**
and was therefore rejected as a complete-oracle architecture. The cheap BDD
cofactors remain useful only as possible future shared predicates; materializing
the recursive evaluator is not viable.

## Structured two-shear continuation (September 10, 2026)

An exhaustive single-shear screen followed by all 870 nonsingular two-shear
compositions, then 24,240 nonsingular three-shear compositions, found a better
encoding. Three successive one-shear extensions around that winner produced
matrix rows `(9,23,21,8,17,32)` and **527 depth / 950 CX / 18 qubits**.
The exact QASM is `artifacts/528/full_mux_feature_linear_528.qasm`, SHA-256
`f83b8695497cca51d13b29e90d6eff184d5cb6def7619511caca79f794192309`.
Exhaustive verification covered all 4096 inputs with maximum error
`1.46e-14` and zero ancilla leakage; five dense full-support checks passed
with maximum error `6.11e-16`. The matching logical QMOD is stored beside the
QASM. This is now the protected local best, although it remains far above the
leaderboard target.

## Pytket post-processing of the 527 candidate (September 10, 2026)

`pytket.FullPeepholeOptimise` and `CliffordSimp` were each applied to the
verified 527/950 QASM, followed by exact U3/CX lowering with
`qubits_initially_zero=False`. Both passes reached **524 depth / 950 CX / 18
qubits**; 100 final Qiskit transpiler seeds did not improve that result.

The exact accepted artifact is
`artifacts/524/full_mux_feature_linear_tket_524.qasm`, SHA-256
`7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147`.
Exhaustive verification covered all 4096 inputs with maximum error
`1.11e-13` and ancilla error `1.84e-14`, both below the verifier threshold.
Five dense checks also passed with maximum error `3.98e-15`. This is the
current local best and is packaged with a logical QMOD companion.

Repeated pytket pass compositions (`FullPeepholeOptimise`, `CliffordSimp`,
`RemoveRedundancies`, and `PeepholeOptimise2Q`) all remained at 524/950. A
native `rz/sx/x/cx` intermediate-basis pipeline followed by exact U3/CX
lowering reached at best 525/950, so it does not replace the accepted 524
artifact.

An assignment-aware post-processing screen then evaluated all 720 physical
feature assignments by raw score and ran pytket on the 30 strongest raw
candidates. Every raw 527/950 tie in that set post-processed to **524/950**;
no assignment improved the accepted result. Thus the critical-wire imbalance
does not expose a remaining assignment-only lever.

## Sparse-Walsh multiplexer experiment (September 10, 2026)

The UCR implementation was changed to visit only nonzero Walsh vertices and
close the resulting Hamming walk, rather than emitting all 64 Gray-cycle
edges per output. The sparse walk was checked against dense UCR behavior and
the complete oracle passed exhaustive verification on all 4096 inputs with
zero ancilla leakage. However, interleaving the variable-length output paths
destroyed the synchronized parallelism of the dense construction: the exact
candidate measured **563 depth / 949 CX / 18 qubits**. The CX reduction is not
worth the depth increase, so this primitive is closed for the current
architecture. Source and metrics are in `src/sparse_mux_feature_encoding.py`
and `artifacts/sparse/`.

## Direct Walsh phase synthesis and pass-composition closure (September 10, 2026)

The direct 12-variable Walsh/GraySynth diagnostic used all **4,096 Walsh
terms**. Its raw exact-basis serialization was **8,168 depth / 4,094 CX / 12
qubits**, already far beyond the protected 524-depth oracle. The exported
phase convention did not pass the logo verifier (phase error 2), so it was not
accepted as an oracle artifact; the result is retained only as a bounded
negative diagnostic against replacing the three synchronized lookup stages
with a dense full Walsh phase polynomial.

## Random complete GL(6,2) output-frame screen (September 10, 2026)

To test beyond the structured shear family, 100 distinct random nonsingular
6-by-6 GF(2) output matrices were compiled through the complete affine-feature
oracle at the fixed winning assignment and routing seeds. The best raw result
was **538 depth / 1,014 CX / 18 qubits**, with matrix rows
`(51,32,47,9,48,36)`. A second raw 538-depth matrix was also checked through
the global pytket pass; the two post-processed results were **533/1006** and
**527/1028**, respectively. Neither improves the accepted 524/950 artifact.

The full bounded screen is recorded in `artifacts/random_affine_screen.json`
and `artifacts/random_affine_screen_post.json`. This is evidence that the
remaining gain is not likely to come from an unstructured output-frame choice;
a new reversible loading or phase primitive is still required.

Alternative pytket compositions on the exact accepted 524-depth QASM,
including `FullPeepholeOptimise`, `CliffordSimp`, `ContextSimp`,
`RemoveRedundancies`, and `OptimisePhaseGadgets` in both orderings, all
lowered to the same **524 / 950 / 18** score. No post-processing improvement
was found.

## Early feature uncompute schedule (September 10, 2026)

The complete raw full-mux schedule was rearranged so that `A` and `B` were
uncomputed immediately after the left-shape phase, before the radius fold and
comparator. Their two-output inverse UCR was interleaved to preserve the
parallel structure, and the remaining `R0,R1,R2,V` inverse was delayed until
after the comparator. The best of eight seeds was **653 depth / 1,010 CX / 18
qubits**, at `artifacts/early_uncompute_ab.qasm` (SHA
`b179123b316a18964d911fb894674656c36c811ded6151d4a9975b0324584a25`).
Exhaustive verification passed all 4096 inputs with zero ancilla leakage. The
extra boundary and partial-UCR serialization outweigh the possible overlap,
so feature-lifetime scheduling is not an improvement over 524/950.

## Direct ESOP left-phase replacement (September 10, 2026)

The three-target x-multiplexer was replaced by the logically equivalent
diagonal phase `A*Square(x) XOR B*Bar(x)`, emitted as eight ESOP-controlled
phase cubes (four for each x interval). The best of eight seeds was
**795 depth / 1,049 CX / 18 qubits** at
`artifacts/direct_left_phase.qasm` (SHA
`e84248ff0ece3b8b6f7a83d9ea962b1ed4b1654afd88adbe58c9bfee9c80a70e`). It
passed exhaustive verification on all 4096 inputs with zero ancilla leakage.
The high-control phase cubes are much more expensive than the synchronized
x-UCR, so direct ESOP phase emission is closed.

## Complete y-input coordinate-frame screen (September 10, 2026)

The affine-feature oracle was wrapped in an invertible linear transformation
of the six y input bits, with every lookup table rewritten through the inverse
map and the input frame restored afterward. The known low-cost input basis
`(1,2,4,40,16,48)` measured **530 depth / 978 CX / 18 qubits**. A bounded
screen of 40 additional random nonsingular input frames found no improvement;
the best random frame measured 536/1020. This confirms that input-coordinate
changes alone do not improve the accepted 524/950 circuit. Results are in
`artifacts/complete_input_basis_screen.json`.

## Complete affine output offsets (September 10, 2026)

The winning six-feature matrix was extended to the full affine family
`G = M F XOR c`. All 64 offsets were compiled. Raw scores were either
**527/950** or **529/950**; the tied offsets were then passed through global
pytket peephole lowering and every one remained **524/950/18**. The complete
screens are `artifacts/complete_affine_offset_screen.json` and
`artifacts/complete_affine_offset_post.json`. The affine output-frame family
therefore provides no further improvement.

## Shared Shannon vector loader (September 10, 2026)

A new loader compiler recursively represented the five-output function as
`f0 XOR y_i*(f0 XOR f1)`, selecting variable splits by an explicit shared
cofactor cost model. It emitted common branches once and used the five output
wires as targets. The exact serialized loader measured **2,385 depth / 1,336
CX / 18 qubits**. A sparse basis-state check covered all 64 y inputs, exact
`(R0,R1,R2,A,B)` output bits, preserved inputs, and clean q17. This is far
worse than the 128-layer synchronized UCR loader, so the first genuinely
shared Shannon compiler is closed as a loader primitive. Source and artifacts:
`src/shared_vector_shannon.py` and `artifacts/shared_vector_shannon_loader*`.

A relative-phase version of the same compiler used dirty-output
`synth_mcx_n_dirty_i15` action/reset blocks. It passed the same 64-input exact
bit-and-cleanup check and reduced the loader to **1,646 depth / 933 CX / 18
qubits** (`artifacts/shared_vector_shannon_rp_loader.qasm`, SHA
`7752f0c9f9beb1ec9f8b9970310c253f9fa641d56a86ef0c2282a2426c362f0f`). The
depth remains far above 128, so relative phase alone does not rescue the
shared Shannon representation.

## Comparator-free threshold phase pilot (September 10, 2026)

`src/threshold_phase_ucr.py` tested a new representation on the existing
six-output loader. After the trusted fold and exact disk guard, every relevant
folded-x row is an affine parity of `V=[r>0]`, `L=[r>=4]`, `T=[r>=6]`,
`P=r&1`, `Q=T&P`, and the already-loaded `B=y5&T`. All 16 guarded folded-x
rows have a representation with no constant term.

The first quantum pilot used bare multiplexed RZ blocks and was rejected
because a non-partitioned UCR contributes an x-dependent zero-branch phase.
The corrected exact version uses MCZ/ESOP phase cubes and exact dirty
compute/phase/uncompute for `T` and `Q`. It passed exhaustive verification;
`artifacts/threshold_phase_ucr_candidate.qasm` has SHA
`5bfb917963e8a237bae9d4db7c3eb8b4000ff0307f0395299a86f425d2dd23b3` and
scores **1265 depth / 1460 CX / 18 qubits**, with zero ancilla leakage. This
is far worse than the protected 524/950/18 circuit. The direct exact-MCZ
threshold replacement is closed; it would need a new shared phase-gadget or
QROM compiler to become competitive.

The follow-up replaced the exact feature cubes with synchronized UCR phase
blocks and synthesized the x-only zero-branch correction as a six-qubit
diagonal. It is a second independently verified implementation of the same
identity: `artifacts/threshold_phase_ucr_ucr_corrected_candidate.qasm`, SHA
`4a6deced9376fd428c177174b695e5c8473f6acf2953f8e8138c4d6879a45845`, scores
**969 depth / 1338 CX / 18 qubits**, with all 4096 inputs checked and zero
ancilla leakage. This is a large improvement over 1265/1460 but remains
negative against 524/950; the correction does not make the architecture
leaderboard-competitive.

## Threshold-feature six-output encoding (September 10, 2026)

The next encoding loaded `[V,L,T,P,A,B]` directly, leaving `T` and `P` as
ordinary outputs and computing only `Q=T&P` transiently into dirty `V`. This
removes the binary radius outputs and comparator while preserving the existing
left-shape phase. The exact serialized result is
`artifacts/threshold_feature_oracle_candidate.qasm`, SHA
`0ccd69c5bd92478aa9df35d27546f0839e3e7894242b1545609fd1da5a5adea4`, at
**781 depth / 1318 CX / 18 qubits**. Exhaustive verification covered all 4096
inputs with maximum error `1.89e-14` and zero ancilla leakage. This improves
the 969-depth branch-corrected pilot but remains negative against the
protected 524/950 result; the threshold-feature encoding is closed.

## Development branch exact rank-batch ESOP diagnostic (September 9, 2026)

`src/rank_batch_exact_esop.py` tested an exact no-ancilla MCX implementation
of the three-term rank batch `(0,1,2)`. It passed the standalone three-term
product verifier on all 4096 inputs, with maximum error `1.21e-14` and zero
ancilla leakage, but serialized to **1431 depth / 823 CX / 18 qubits**. The
artifact is `artifacts/rank_batch_exact_esop_012_development.qasm`, SHA
`ec84910237b1ef9fae762ab21af832bd09db9947375ffa19ccd743d2b55fb49b`.
This closes exact per-cube MCX loading as a depth improvement over the
257-depth UCR batch.

## Development branch direct bilinear phase synthesis (September 9, 2026)

The existing diagonal phase-cube compiler was applied directly to rank-factor
ESOP products, without materializing either factor. Individual rank terms were
correct and relatively small: term 0 measured **66/52**, term 1 **199/119**,
and term 2 **251/162**; each passed exhaustive product-term verification.

The complete rank-10 expansion reduced to 69 diagonal cubes. A 20-seed search
found a best complete candidate at **1725 depth / 1235 CX / 18 qubits**. The
candidate `artifacts/rank_phase_only_full_development.qasm` passed the complete
logo verifier on all 4096 inputs with zero ancilla leakage; SHA-256:
`f4ed4e259eb477fcfd72bf721937963c00270624924ab6bc14e05766b639d882`.
This closes unshared direct bilinear phase expansion. The remaining
opportunity is global sharing of phase cubes or a different multi-output
representation; per-term phase synthesis alone is insufficient.

An exact-MCZ serialization of the same 69-cube phase-only construction was
also checked at **1734/1235/18** (SHA
`af295b60cd6f48c8eebde5fd05d6539556bbdb40f14c547b13beeda727759f32`). It
passed all 4096 inputs but is slightly deeper than the 1725/1235 version, so
the MCZ replacement is closed as well.

The same global cube-sharing recursion was rerun with `mcz.best_mcz` replacing
the older phase-cube primitive. The best of eight seeds was **1734 depth /
1235 CX / 18 qubits**, and it passed complete exhaustive verification with
zero ancilla leakage. SHA-256:
`af295b60cd6f48c8eebde5fd05d6539556bbdb40f14c547b13beeda727759f32`.
This is slightly worse than the 1725-depth phase-only result, so MCZ helper
selection is not the missing improvement.

## Development branch phase-rank basis search (September 9, 2026)

An elementary GF(2) basis search scored complete serialized direct phase-only
circuits after each mutation. The best of 100 steps kept depth at **1725** but
reduced CX count from 1235 to **1225**. The candidate
`artifacts/phase_rank_basis_best_development.qasm` passed the complete logo
verifier on all 4096 inputs with zero ancilla leakage; SHA-256:
`f6d52201ba8f066b388d2a25d94a1348b6b14625f024263de53c3fb4a06c5542`.
The search data is `artifacts/phase_rank_basis_search_development.json`.
Basis choice changes cube sharing and CX count but did not change the depth
regime, so this is a verified near-miss rather than a replacement for 524.

## Development branch grouped phase-sharing pilot (September 9, 2026)

The 69 direct bilinear phase cubes contain 23 distinct y-side ESOP cubes.
`src/shared_y_phase_grouped.py` computes one y-cube into q17, synthesizes all
associated x-side phase cubes with a shared q17 control, then uncomputes q17.
This reduces the naive grouped-y implementation from 4100 depth to a verified
**2242 depth / 1624 CX / 18 qubits**. The complete candidate
`artifacts/shared_y_phase_grouped_development.qasm` passed all 4096 logo inputs
with zero ancilla leakage; SHA-256:
`d18d1530e7615e64fab0bdd1a2a13e32e685a005966fd6b6f1c4f31d78eb4f29`.
It remains above both the protected 524-depth oracle and the 1725-depth global
phase-only candidate, so local y-group sharing is insufficient.

## Standalone retained-product verification (September 9, 2026)

Two separately generated term-0 retained-product diagnostics were checked
directly with `src/verify_product_term.py` over all 4096 `(x,y)` inputs. The
phase-retention variant `artifacts/direct_product_retention_term0_development.qasm`
is exact at **162 depth / 173 CX / 18 qubits**, with maximum error
`2.93e-15` and zero ancilla leakage (SHA
`636e9f66f5d6a4af275a9335919275f6b1c21d4e7a10ef658733f1a453649f4d`). A
standard exact-control comparison is exact at **243/243/18**. These are
single-product components only; they do not constitute a complete logo
oracle, and the current reproducible exact-retention builder remains the
separate 508/407 term-0 baseline.

Global pytket `FullPeepholeOptimise` and `CliffordSimp` rewrites were applied
to the verified UCR batch. Both preserved the three-term product semantics but
returned exactly **257 depth / 535 CX**; their serialized outputs share SHA
`332524c727f4c0dd5491cd6524656e3d09f798a1f242955f83d712246e15bed6`. This
closes compiler-only post-processing for this batch.

## Cofactor/Shannon three-output rank-bank pilot (September 10, 2026)

The generic Shannon/Davio cofactor emitter in `src/qrom_tree.py` was adapted
to the three rank factors `(0,1,2)` in `src/cofactor_rank_bank.py`. It shares
cofactor branches within each six-input, three-output bank and then applies
three CZ phase couplings before exact inverse cleanup. This is a bank-level
control experiment, not a complete logo oracle.

The clean-workspace control is exact but not competitive:
`artifacts/cofactor_rank_bank_012_clean_development.qasm` measures **1330
depth / 767 CX / 18 qubits**, SHA
`f1f619b1077985bd5b4ad05835ddb564ff533142a3eb5378f58a4eb1f65f0e6b`. Its
product-phase verifier checked all 4096 `(x,y)` inputs, with maximum error
`1.20e-14` and zero ancilla leakage. The two abstract cofactor tree scores
were 203 and 158 for the x and y banks; the serialized cost is dominated by
exact bank interactions and cleanup.

Offering the other bank's live output wires as scratch produced an apparently
promising **309 / 205 / 18** candidate at
`artifacts/cofactor_rank_bank_012_cross_dirty_development.qasm`, but exhaustive
product verification failed with phase error 2. Replacing every RCCX in the
tree emitter with exact CCX did not repair the dirty semantics: the resulting
`artifacts/cofactor_rank_bank_012_cross_dirty_exact_development.qasm` measured
**501 / 359 / 18** and also failed with phase error 2. These failures show that
the recursive Shannon/Davio program assumes more than a merely available
dirty wire; its branch/frame invariant is not preserved when a live output
bank is used as scratch. The files are retained as invalid diagnostics, not
candidate improvements.

This pilot does not justify a rank-basis search. A useful continuation needs
an explicit conditionally-clean or dirty-frame invariant in the cofactor
compiler, with verification after every bank and phase boundary; ordinary
borrowed-output substitution is closed.

## Exact one-live-pair transition stream (September 10, 2026)

The proposed stateful stream was implemented in `src/exact_stream.py`. Unlike
the historical `src/stream.py`, it uses exact-control transitions
`q12 ^= a_i XOR a_j` and `q13 ^= b_i XOR b_j`, keeps one live factor pair,
applies one CZ per rank term, and returns to zero with one final transition.
Every transition was compiled with explicit clean scratch and
`qubits_initially_zero=False`. All unordered edges among zero plus the ten
terms were scored in native `u3`/`cx` form, then a Held--Karp path search chose
the complete order.

The three complete candidates all passed exhaustive verification over 4096
logo inputs with zero ancilla leakage:

| Basis | Native order (zero-based term indices) | Depth | CX | SHA |
|---|---|---:|---:|---|
| `pair_terms` | `9,5,3,6,7,8,0,2,1,4` | **1227** | **1361** | `f44158faeac79cd6623b893d78fa00a505471f96ca90040be81229f1ce2cd3d1` |
| `rank_terms` | `7,6,8,9,5,3,4,1,2,0` | **1267** | **1322** | `ae80e69fb962422f9b81b4b650742d51ab9e04c58e9641b0c0d865d69299913a` |
| `rank_mc_pareto_terms` | `6,0,2,8,7,5,1,9,3,4` | **1303** | **1455** | `dd7c71425f88f96ec24363e21f54b2494039943cff929c74862d8a73cfb261ff` |

The best exact stream also passed five dense full-support checks with maximum
error `5.69e-16`. This is decisively above the proposed 400-depth cutoff and
above the protected 524/950 oracle. Exact one-live-pair streaming is therefore
closed; a relative-phase ledger on the same one-pair transition primitive is
not justified by this baseline.

## Exact two-live-pair vector stream (September 10, 2026)

The next stateful variant kept two x/y factor pairs live in q12..q15 and used
q16,q17 as explicitly clean transition scratch. Five consecutive two-term
groups were streamed with two parallel CZ gates per state. Exact native edge
costs and a Held--Karp ordering were evaluated for all three current bases.

The complete candidates were all exhaustively verified with zero ancilla
leakage:

| Basis | Depth | CX | SHA |
|---|---:|---:|---|
| `pair_terms` | **2948** | **1702** | `1b89f2629fa55458f7fb6ed5504f01f8dde6ee9f35114727c9007250d3b1bb8b` |
| `rank_terms` | **2774** | **1601** | `0a9645c3da51b5d035da0ec60296337137ec06e3dbc13d22ff974f2a5fdd8677` |
| `rank_mc_pareto_terms` | **2716** | **1576** | `9192b7837d911385b2db0b6968a52e2727a8c2970c70acab301095345cd42720` |

This fixed two-term grouping is decisively worse than both the exact one-pair
stream and the protected 524/950 oracle. It is retained as a bounded negative
diagnostic; no partition search or relative-phase extension is justified for
this exact transition primitive.

## Explicit HP24 cofactor lowering (September 10, 2026)

The remaining bounded cofactor check replaced `qrom_tree.emit()`'s generic
high-control fallback and relative-phase three-control leaf with explicit
exact HP24 no-ancilla MCX synthesis in `src/cofactor_rank_bank_hp24.py`.
The three-term clean bank candidate
`artifacts/cofactor_rank_bank_012_hp24_development.qasm` measures **1611 depth
/ 1895 CX / 18 qubits**, SHA
`ed81bf69e55db8fc72bfa168c9a5b7aeecd2ac4f9049425fbfc79053109f654a`.
It passed the standalone three-term product verifier over all 4096 inputs with
maximum error `1.14e-14` and zero ancilla leakage, but is worse than the
existing cofactor control and the 257/535 UCR batch. Explicit HP24 lowering
therefore does not rescue the cofactor architecture.

## Cofactor temporary-product phase pilot (September 10, 2026)

The next phase/state-duality test avoided a second live y bank. In
`src/cofactor_product_phase.py`, the x factors for terms `(0,1,2)` are loaded
with the cofactor bank, each y factor is emitted directly as an ESOP phase
conditioned on its live x output, and the x bank is uncomputed afterward. The
three cofactor scratch wires are restored before every phase cube.

The exact candidate `artifacts/cofactor_product_phase_012_development.qasm`
measures **484 depth / 290 CX / 18 qubits**, SHA
`66e27f13d5b28455b4d721e80eff95712328d4a96e8d12fff65f22df4dfa4512`. Its
product-phase verifier checked all 4096 inputs with maximum error
`1.10e-14` and zero ancilla leakage. The result is a useful phase-safe
control, but it is worse than the existing 257/535 three-term UCR batch; the
cofactor bank's 20-layer raw compute is outweighed by direct high-control y
phase cubes. Scaling this exact formulation to all ten terms is therefore not
justified without a shared phase-gadget compiler.

## Complete cofactor phase integration (September 10, 2026)

The three-term phase pilot was integrated across all ten rank terms using
groups `(0,1,2)`, `(3,4,5)`, `(6,7,8)`, and `(9,)` in
`src/cofactor_full_oracle.py`. Each group restores all six ancillas before the
next group. The complete standalone candidate is
`artifacts/cofactor_full_rank_phase_development.qasm` at **1685 depth / 1026
CX / 18 qubits**, SHA
`ed6d6168559f968e29905468f2ef59ecc1bc30c740a2850c26c43916baaa1422`.

The exact serialized QASM passed exhaustive verification on all 4096 logo
inputs with maximum error `2.60e-14`, zero ancilla leakage, and matching SHA.
Five dense full-support states also passed with maximum error `4.89e-16`.
This is the required full-problem score for the architecture, and it is far
worse than the protected 524/950 oracle. The cofactor temporary-product route
is therefore closed in this form; further work would need a fundamentally
shared phase-gadget primitive rather than more term grouping.

## Architecture closure decision (September 10, 2026)

The following branches are now closed as primary optimization directions:

1. **Stateful factor streaming:** exact one-live-pair streaming bottoms out at
   1227/1361/18 across the tested bases.
2. **Multi-live-factor streaming:** exact two-live-pair streaming bottoms out
   at 2716/1576/18 in the tested grouping.
3. **Shannon/cofactor materialization:** clean cofactor banks and explicit
   HP24 lowering remain far above the protected circuit; dirty variants fail
   exact phase verification.

These closures are architectural, not claims that no conceivable relative-
phase or conditionally-clean construction could work. However, the measured
gaps are large enough that incremental variants of these same representations
are not justified. The protected complete baseline remains
`artifacts/524/full_mux_feature_linear_tket_524.qasm` at **524 depth / 950 CX /
18 qubits**, with its matching exhaustive and dense verification reports.

## Conditionally-clean cofactor screening (September 10, 2026)

The proposed selector splits were regenerated directly from `search.logo` in
`src/conditionally_clean_cofactor.py`. The results match the independent
truth-table analysis: selectors `(x5,y5)`, `(x5,y4,y5)`, `(x5,y3,y4,y5)`, and
`(x5,y2,y3,y4,y5)` produce respectively 4, 6, 9, and 16 nonzero branches;
their residual rank profiles are recorded in
`artifacts/conditionally_clean_screen.json`.

The first quantum test used the hardest rank-4 branch of the four-bit split,
assignment `x5=1,y3=1,y4=0,y5=0`. A conservative reference compiler that uses
no borrowed selector workspace produced
`artifacts/conditionally_clean_branch_3_safe.qasm` at **946 depth / 518 CX /
18 qubits**. The branch-specific exhaustive report is
`artifacts/conditionally_clean_branch_3_safe.exhaustive.json`, SHA
`e1d5e0aac10a66540bef161651df590a9357fba18774f59f50ff1438688adcdd`.

The first conditionally-clean implementation then normalized the selector
wires only under the branch flag and used Qiskit's dirty-ancilla MCX chain for
the residual ESOP phase cubes. The serialized candidate
`artifacts/conditionally_clean_branch_3_borrowed.qasm` measures **904 depth /
522 CX / 18 qubits**, SHA
`70c32ab29c4fd7d9af61fcf21fb2d59ef0bece7fec3fe2c9193b80a379785a0c`. It
passed the branch-specific exhaustive check with zero ancilla leakage and
maximum error `7.06e-15`; this check targets only the selected cofactor, not
the complete logo oracle.

This is an exact and safe implementation of the workspace mechanism, but it
fails the local 30--50 depth viability gate by a wide margin. The negative
result is specifically against independent ESOP phase-cube lowering. A final
bounded follow-up would need representation-level factoring of the residual
truth table; full nine-branch integration is not justified before that test.

## Cofactor representation and selector scan (September 10, 2026)

The branch-3 ESOP profile contains 11 cubes and 67 literals. Its residual
control-size histogram is `{2:1, 5:1, 6:4, 7:4, 8:1}`. It has 12 cube
containment relationships; the most frequent literal pair occurs in 10 cubes,
and the aggregate repeated-pair score is 155. This confirms that the 904-depth
result is dominated by representation lowering rather than a lack of Boolean
structure.

All `C(12,3)=220`, `C(12,4)=495`, and `C(12,5)=792` selector sets were then
screened classically. The full structural scan is
`artifacts/conditionally_clean_selector_scan.json`; it records nonzero
branches, ESOP cubes/literals, control histograms, containment, and repeated
literal-pair signatures. By raw ESOP size, the best four-bit selector is
`(x5,y2,y4,y5)` with 11 nonzero branches and 68 total cubes; the tested
`(x5,y3,y4,y5)` selector has 9 branches and 70 total cubes. Rank alone is
therefore not a sufficient selector criterion. These are prescreening results,
not native-depth results; the next experiment must factor the branch truth
table before compiling the Pareto winners.

## Dominant-pair factored XAG pilot (September 10, 2026)

The branch-3 profile's most frequent support pair is `(x4,y2)`. Its useful
signed factor is `P = (x4=0) AND (y2=1)`, which occurs in seven exact cubes;
the remaining polarity variants are retained in an explicit remainder rather
than being incorrectly treated as the same signed cube. Removing `P` gives a
six-variable residual `G` with 49 marked inputs. The bounded `minmc_xag.py`
solver found an exact six-node XAG for `G`; one node is affine and folds into
the output, so the reversible pilot uses five nonlinear nodes. The exceptional
remainder has six marked inputs and four ESOP cubes.

The resulting local branch candidate
`artifacts/conditionally_clean_branch_3_factored.qasm` measures **713 depth /
445 CX / 18 qubits**, SHA
`611c3f8a51595fbca49102b6f6c4728ea6c96b7966834e417308669b4a7fef1c`. It
passed the branch-specific exhaustive verifier with maximum error `7.16e-15`,
zero ancilla leakage, and matching SHA. This is a 21% depth and 15% CX
reduction against the 904/522 independent-ESOP candidate, confirming that
representation-level factoring is the correct lever. It is still far above
the 30--50 local viability gate, so full branch integration remains deferred.

## Factored-component ablations and whole-branch XAG screen (September 10, 2026)

The 713-depth factored pilot was decomposed using the same selector and exact
branch verifier. The common-factor/XAG component `P*G` measured **323 depth /
249 CX**, while the exceptional remainder `R` measured **459 depth / 248 CX**.
Both passed their exact extracted-predicate checks with zero ancilla leakage;
their matching QASM hashes are recorded in the exhaustive reports beside
`artifacts/conditionally_clean_branch_3_factored_pg.qasm` and
`artifacts/conditionally_clean_branch_3_factored_r.qasm`. The remainder is
therefore a major cost center, but the factor/XAG plumbing is also too deep for
the target.

The bounded exact eight-variable XAG search in `src/xag8_bounded.py` proved
unsatisfiable through two AND nodes, then returned `unknown` at three and four
nodes under 5-second solver budgets. It produced no candidate and is not an
impossibility result. This closes the cheap whole-branch XAG screen; a larger
search is not justified until the native lowering is redesigned or a stronger
XAG/decoder backend is selected.

## Conditional-clean cofactor/XAG branch closure (September 10, 2026)

The conditional-clean mechanism is verified and reusable, but this specific
cofactor/XAG implementation line is now closed for the competition objective.
The decisive exact ablations are **D(PG)=323**, **D(R)=459**, and
**D(PG XOR R)=713**, all far above the complete-oracle target below 190. The
bounded whole-branch XAG search provided no positive signal: it found no model
through two AND nodes and returned `unknown` at three and four nodes. That is
not a lower-bound proof, but it does not justify more time on this lowering
architecture. Preserve the diagnostics as a valid negative result and do not
integrate all selector branches. The protected baseline remains
`artifacts/524/full_mux_feature_linear_tket_524.qasm` at **524/950/18**.

## Finite-size Lupanov branch pilot (September 10, 2026)

The proposed rich-width experiment was implemented in
`src/lupanov_branch.py` using the literal finite-size `q=1`, `p=7` instance
of the Nie--Zi/Lupanov decomposition. The resource audit matters: with only
10 effective workspace wires, the explicit rich-function bound already rules
out `q=2`; the smallest directly valid parameterization therefore iterates
128 seven-bit prefix cofactors. The Boolean output was converted to the
competition phase oracle by compute--Z--uncompute.

The exact serialized candidate
`artifacts/lupanov_branch_q1.qasm` measures **20432 depth / 11260 CX / 18
qubits**, SHA
`f91ad1511021a2f045be32df47b45a7ba127fa5eef414fb4e72b1e6bcbbed80a`. Its
local eight-input exhaustive verifier checked all 256 residual inputs with
maximum error `1.61e-13` and ancilla error `5.78e-15`.

This is a decisive negative finite-size result under the proposed cutoff. It
does not contradict the asymptotic theorem or prove that every possible
constant-optimized implementation is large; it shows that the literal
rich-width construction does not instantiate competitively at `n=8,m=10`.
Do not integrate the nine branches. The protected complete baseline remains
`artifacts/524/full_mux_feature_linear_tket_524.qasm` at **524/950/18**.
## Exact depth-window pilot (September 9, 2026)

The protected baseline was scheduled with an ASAP/ALAP analysis. Its input
SHA is `7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147`;
the schedule confirms **524 depth / 950 CX**, with 580 zero-slack gates. The
largest CNOT+diagonal run is layers 127--257, but it spans 14 qubits and is
not a small local synthesis target. The complete profile is in
`artifacts/524/full_mux_feature_linear_tket_524.window_profile.json`.

A strict exact-unitary splice pilot then tested the first contiguous late
3-wire windows. Layers 483--487 and 498--504 gave no change: both local and
global scores remained 524 depth / 950 CX. Two larger late windows were
rejected because their serialized gate ranges were interleaved with unrelated
operations. This is a negative result for ordinary small exact peepholes, not
for reachable-subspace resynthesis. See
`artifacts/524/full_mux_feature_linear_tket_524.strict_window_pilot.json` and
`src/strict_window_pilot.py`.
## DAG and semantic-window preparation (September 9, 2026)

`src/dag_window_resynthesis.py` now inventories dependency-closed slabs rather
than serialized gate ranges. Within the 3--6-wire, 12--50-layer bounded search,
19 candidates were recovered; two late candidates remain serialized-interleaved
while having no dependency crossing inside the selected active wires. This
demonstrates that the rejected textual windows were not the whole DAG search,
but the inventory is analysis-only and has not yet produced a replacement.

`src/semantic_window.py` emits exact 64-state mappings for `(R0,R1)`, `(R1,R2)`,
`(A,B)`, and `(A,B,V)` from `|y>|0...0>`. `src/semantic_cost.py` measures strict
Walsh references at 128/128, 109/110, 128/128, and 128/172 depth/CX. BQSKit
1.2.1 is installed in the project `.venv`; its 8-qubit, 64-state QSearch
smoke test at max layer 2 exceeded a 60-second bound. No semantic numerical
candidate or score improvement exists yet.

## Discrete shared-XAG screen (September 9, 2026)

The first custom multi-output solver, `src/multioutput_minmc.py`, represents
all 64 y-input rows as one machine-word truth signature and searches shared
affine-AND nodes for pairs/triples. The shallow report is
`artifacts/semantic_discrete/joint_xag_results.json`. No model was returned
through three shared AND nodes for `(R0,R1)`, `(R1,R2)`, `(A,B)`, or `(A,B,V)`
under 1-second-per-bound limits. Because each bound timed out or remained
unresolved, this is not an impossibility result and does not justify native
RCCX lowering yet. The protected baseline remains 524/950.
