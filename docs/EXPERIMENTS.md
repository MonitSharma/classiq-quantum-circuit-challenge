# Experiment history and failure notes

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

## Ideas considered but not implemented or validated

- PyZX/pytket global simplification of compute/phase/uncompute: packages installed; next concrete experiment.
- Fold/translate y before lookup to lower control count: likely savings compete with constant adders, region guards, and exceptional rows. No tested win.
- Encode row classes and column thresholds into three ancillas each, then compare: possible parallel lookups, unresolved guard complexity.
- Align disks with a conditional high-x transformation involving y5*x5 while preserving left shapes: only a hypothesis.
- Alternative radius flags V, L=(r>=4), T=(r>=6), P=odd. Then r>=5 is T OR P, r>=7 is T AND P; for the current table, bar-y flag equals y5 AND T. Could reduce lookup duplication but needs a new reversible phase/comparator design.
- More control-order seed search alone is unlikely to bridge the remaining 245 depth to the observed leader.

## Verification tools

`exhaustive_verify.py` parses the saved QASM and sparsely simulates every clean-ancilla basis input together. It tracks coordinate mapping, diagonal phase, ancilla leakage, and a numerical discarded-amplitude bound. It aborts if sparse support exceeds 2048; a more mixing optimizer may require a blocked dense verifier instead. The current best peaks at support 64.

`verify.py` uses Qiskit Aer on random dense complex superpositions over all coordinates, compares the full output including ancillas, and maintains a shared global phase across tests. This is an independent simulation path, but probabilistic. It has now also passed on the current 536-depth best with five random dense states.

A phase-only truth-table check that ignores relative phases or dirty ancillas is insufficient. Always verify the exact exported standalone circuit, not just its high-level Boolean formula or its behavior on a uniform input.
