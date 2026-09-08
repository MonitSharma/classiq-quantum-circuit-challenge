# Experiment history and failure notes

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

### Berkeley ABC AIG diagnostic: negative classical lower-level route

The built `experiments/abc/abc` binary was run on the exact 12-input logo
benchmark. Its `dc2` flow reached 224 AND nodes at level 22; the balanced
rewrite/refactor flow remained at 247 nodes and level 17, and `syn2` remained
at 247 nodes and level 19. These are classical AIG measurements, not quantum
scores, but they show that ABC does not expose a compact hidden computation
graph suitable for the six-clean-ancilla reversible compiler.
