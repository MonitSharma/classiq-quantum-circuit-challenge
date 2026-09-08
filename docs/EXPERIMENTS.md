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
