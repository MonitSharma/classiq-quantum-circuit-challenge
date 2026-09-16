# Complete Classiq logo-oracle method postmortem

Date: 2026-09-16

## Executive summary

This document consolidates the methods represented by the repository's source,
experiment artifacts, and Markdown research record. It is a map of what was
tried, where it lives, what was measured, and why each line did or did not
become the protected submission.

The task is an exact standalone `u3`/`cx` oracle for

```text
U|x,y,0^6> = (-1)^logo(x,y)|x,y,0^6>
```

with arbitrary q[0:12], six clean/restored ancillas q[12:18], at most 18
qubits, and one shared global phase allowed. A result is considered verified
only when the serialized QASM itself passes exhaustive verification and the
report SHA matches that exact file.

The current protected best, according to the current `AGENTS.md` and
`docs/HANDOFF.md`, is **185 depth / 854 CX / 18 qubits** in `artifacts/185/`.
The repository also preserves later historical packages, including 186, 188,
190, 193, 196, 198, 218, 221, 222, 224, 243, 258 and fallback packages. Those
later-numbered records must not be mistaken for the currently protected
submission without checking their provenance and the current handoff.

The September 15 leaderboard screenshot records a 137-depth external leader;
no local artifact establishes rank one.

## How to read the outcomes

- **Verified** means exact-file exhaustive verification, not merely a Boolean
  score or a component check.
- **Exact but uncompetitive** means the circuit computes the required oracle
  but loses on native depth, CNOT count, width, or some combination.
- **Heuristic negative** means the bounded search found no candidate; it is not
  an impossibility proof.
- **UNSAT** applies only to the exact constrained formulation that was solved.
- **UNKNOWN / timeout** is not UNSAT and cannot close the larger family.
- **Control** means an implementation/serialization check, not evidence that a
  search method solved the logo.

## Verified progression

| Family checkpoint | Result | What it taught us |
|---|---:|---|
| Original notebook / rectangle construction | 5329 / 3502 / 18 | Correct baseline, but far too deep |
| XAG/rank construction | 1046 / 903 | Classical factoring alone did not solve native depth |
| Pair construction | 779 / 736 | Exact pair decomposition is possible; earlier 688 claim was invalid |
| Radius/UCR architecture | 682 / 740 | Shared-radius multiplexing improved the baseline |
| Parallel six-feature UCR | 536 / 1020 | Major architectural reduction |
| Feature-linear/Tket fallback | 524 / 950 / 18 | Protected older fallback; exact and preserved |
| Package 531 | 531 / 1020 / 18 | Historical packaged fallback |
| Two-stage class-code family | 258 / 1188, then 243 / 971 | Raw-bit-assisted class encoding and integer phase lifts worked, but remained above 185 |
| 224 / 957 and 222 / 945 | Exact historical packages | Parity-assisted codes and relative-phase boundary changes improved the 258 family |
| 218 / 897 | Exact historical package | Integer full-turn cube phase representation and joint scheduling helped kernel depth |
| 193 / 853 | Exact historical package | CX tie-breaker improvement only; depth stayed 193 |
| 190 / 857 | Exact protected historical package | Earlier protected best before the current 185 record |
| 188 / 855 and 186 / 855 | Exact historical packages | Phase reordering/fusion gave small depth movements |
| 185 / 854 / 18 | Current protected best | CNOT rewrites, safe scheduling, and exact verification established the current checkpoint |

All package-level numbers above are historical measurements; the current
protected artifact and its replay instructions take precedence.

## Method families and failure analysis

### 1. Direct Classiq, notebook, arithmetic, and model-first synthesis

Locations include `src/class_oracle.py`, `src/classiq_lookup.py`,
`src/classiq_search.py`, `src/classiq_variants.py`, `src/classiq_bits.py`,
`src/build_and_oracle.py`, `src/build_bridge_oracle.py`,
`src/two_stage_oracle.py`, `src/level_oracle.py`, and the arithmetic/geometry
builders. The historical discussion is in `docs/EXPERIMENTS.md`,
`docs/CURRENT_DESIGN.md`, `docs/CLASSICAL_STRUCTURE.md`,
`docs/LEVEL_COMPARATOR.md`, and `docs/POST190_ARITHMETIC_SCHEDULE.md`.

What was tried:

- direct rectangle and Classiq notebook synthesis;
- arithmetic radius/interval formulas and y-side folds;
- row-class, column-class, comparator, level, and direct-geometry models;
- low-rank arithmetic and lookup formulations;
- Classiq model-only probes and native QMOD generation.

Why it failed:

- the original rectangle oracle was correct but depth 5329;
- arithmetic models expanded to 82 qubits or paid large fold/ripple costs;
- the measured y-fold cost was about 95 layers and did not satisfy the desired
  descriptor budget;
- direct geometry and interval/radius variants produced thousands of layers;
- some backend requests did not return useful fresh QASM, so they are not
  evidence of a universal Classiq limitation.

The successful lesson was not “use more arithmetic”; it was to load a small
set of structured features into six clean wires and phase them conditionally.

### 2. Pair, radius, UCR, feature frames, and multiplexors

Locations include `src/pair_search.py`, `src/pair_variants.py`,
`src/pair_boundary_search.py`, `src/radius.py`, `src/radius_mux.py`,
`src/full_mux.py`, `src/full_mux_derive_v.py`, `src/hybrid_a_mux.py`,
`src/hybrid_ab_mux.py`, `src/direct_feature_mux.py`,
`src/feature_linear_encoding.py`, `src/build_distributed_best.py`,
and `src/distributed_level_oracle.py`. Main records are
`docs/CURRENT_DESIGN.md`, `docs/HYBRID_AFFINE_REPORT.md`,
`docs/DISTRIBUTED_LOOKUP_258.md`, and `docs/POST258_RESEARCH.md`.

What worked:

- pair decomposition and shared-radius UCRs made the first large reductions;
- six parallel features `(R0,R1,R2,A,B,V)` reached the 536 and then 524
  fallback family;
- affine output frames, physical feature permutations, safe rebasing, and
  Tket/Pytket post-processing produced exact verified packages.

Why further optimization failed:

- q16 in the 524 circuit participates in about 405 operations, including 206
  CXs; its fixed wire-touch schedule became the dominant local floor;
- changing feature assignment or transpiler seeds mostly traded CX against
  depth;
- ordinary CNOT/peephole optimization could not remove the lifetime and
  uncompute costs of the loaded features;
- six clean ancillas are too few to make all feature phases parallel.

This family produced the best practical fallback, but the fixed implementation
does not explain the external 137-depth leader and was eventually treated as
architecturally closed.

### 3. Geometry, disjoint rectangles, shells, thresholds, and Shannon forms

Locations include `src/disjoint_rectangles.py`, `src/disjoint_geometry_check.py`,
`src/disjoint_geometry_oracle.py`, `src/disjoint_hybrid_geometry.py`,
`src/disjoint_hybrid_oracle.py`, `src/disjoint_shared_rectangle.py`,
`src/threshold_shell.py`, `src/threshold_feature_oracle.py`,
`src/search_lut_supports.py`, `src/shared_vector_shannon.py`, and
`src/shared_vector_shannon_rp.py`. Records include
`docs/DISJOINT_GEOMETRY_REPORT.md`, `docs/THREE_SWEEP.md`,
`docs/CLASSICAL_STRUCTURE.md`, and `docs/RESEARCH_CLOSURE_2026-09-11.md`.

The exact geometric decomposition and shell/threshold forms were useful for
understanding the nested disk structure. Their failure was native cost:
component loaders and decoders were individually manageable, but composing and
uncomputing them produced depths from hundreds to several thousand layers.
The disjoint architecture was verified in components and in complete exact
oracles, but no version beat the protected family.

### 4. Three-sweep, row-pair, column-pair, and reachable parity decoders

Locations include the `src/three_sweep/` package, `src/three_plus_three_native.py`,
`src/three_sweep/phase_factorization.py`, `src/three_sweep/reachable_phase_poly.py`,
and `src/three_sweep/reachable_column_phase_poly.py`. The consolidated record is
`docs/THREE_SWEEP.md` and `docs/VECTOR_LOADER_REPORT.md`.

What was established:

- row-pair and transposed column-pair loaders can be verified in roughly the
  52–65-layer component range;
- phase-rank and reachable-state parity sharing are real structural effects;
- some loaders are exact and useful as diagnostics.

Why it failed as a full oracle:

- exact decoder and shell-sharing compositions reached roughly 3800+ layers;
- lower rotation counts did not imply lower total `u3`/`cx` depth;
- the architecture required more phase/uncompute structure than the six
  ancillas can support cheaply.

### 5. Rank, ANF, ESOP, XAG, min-MC, and Boolean factoring

Locations include `src/factor.py`, `src/rank.py`, `src/rank_factor_inventory.py`,
`src/minmc_rank_pair.py`, `src/minmc_xag.py`, `src/multioutput_minmc.py`,
`src/multioutput_xag_selection.py`, `src/xag.py`, `src/xag_affine.py`,
`src/xag_basis.py`, `src/destructive_xag.py`, `src/destructive_xag_rank.py`,
`src/destructive_dc_esop.py`, `src/destructive_linear_basis_esop.py`,
`src/decode_xag.py`, and `src/high_order_affine_exact_esop*.py`.
Records include `docs/MINMC_RANK_REPORT.md`, `docs/HYBRID_AFFINE_REPORT.md`,
`docs/MULTIPLICATIVE_DEPTH.md`, `docs/PHASE_PEBBLE_REPORT.md`, and the Boolean
sections of `docs/EXPERIMENTS.md`.

What worked:

- exact classical XAGs and ANF/ESOP factorizations were found;
- minimum-multiplicative-complexity databases and Mockturtle witnesses were
  integrated;
- low-MD XAGs (including MD4/MD6 records) exist as algebraic objects.

Why they failed natively:

- classical AND count ignores live-value lifetime, recomputation, dirty-target
  restoration, relative phase, and routing;
- the original 97-AND exact XAG had a measured peak of about 22 live registers,
  beyond the available 18 wires once the predicate is reserved;
- original-order affine live rank reached about 34, with the best ready-node
  schedule still around rank 22;
- rematerialization, dirty-span, repeated-product, and ESOP screens did not
  produce an exact phase frontier;
- MD4/MD6 algebraic depth did not translate into a low native depth: reported
  realizations were roughly 1023/899 or worse.

The resulting closure is empirical and applies to the tested compiler models,
not to all possible reversible embeddings.

### 6. Destructive semantic classifiers and approximate residual search

Locations include `src/destructive_semantic_search.py`,
`src/destructive_classifier.py`, `src/destructive_dirty_search.py`,
`src/destructive_xag_scheduler.py`, `src/destructive_xag_rank.py`,
`src/destructive_linear_basis_esop.py`, `src/dirty_esop_pair.py`,
`src/conditionally_clean_cofactor.py`, `src/fredkin_semantic_screen.py`, and
the many `src/high_order_affine_*` variants. Records are
`docs/DESTRUCTIVE_CLASSIFIER_PLAN.md`, `docs/DESTRUCTIVE_SEMANTIC_SEARCH.md`,
`docs/POST190_REGISTER_IMPLEMENTATION.md`, and
`docs/POST190_WHOLE_SCHEDULE_CLOSURE.md`.

The semantic engine correctly models 4096 coordinate inputs using Boolean truth
tables. It explored:

- clean and dirty completion;
- high-order affine corrections and signed controls;
- direct output accumulators and affine/biaffine RCCX controls;
- controlled swaps/Fredkin variants;
- repeated products, exact-distance frontiers, and global phase-edge retention;
- ESOP completion with reachable-state don't-cares;
- destructive order searches from roughly 12 through 19 RCCX layers.

Failure modes:

- approximate residual reduction did not yield exact target completion within
  the available width;
- exact completion often expanded to thousands of native layers;
- one-use register allocation and rank-constrained rematerialization were too
  restrictive, while relaxed dirty variants still had no phase frontier;
- some historical candidates contain semantic metadata that cannot be
  reproduced from their saved gate list under the current replay code. The
  whole-schedule closure report records this rather than silently trusting the
  metadata.

The final non-monotone whole-schedule pilot corrected CX resource accounting,
validated suffix replay, and compared tail-only, one-global-gate, and full
interior mutation. Best current replay residuals were 537 and 565 in the two
imported basins; no exact classifier or structural/native improvement emerged.

### 7. Multiplicative-depth, affine-frame, and shared-XAG searches

Locations include `src/multiplicative_depth_analysis.py`,
`src/audit_multiplicative_depth.py`, `src/md_xag.py`, `src/md_ordered_quantum.py`,
`src/md_xag_quantum.py`, `src/affine.py`, `src/affine_frame.py`,
`src/affine_shared_search.py`, `src/affine_md_search.py`,
`src/semantic_subspace_xag.py`, `src/semantic_xag_completion.py`,
`src/post190_relative_xag*.py`, and `src/post190_structured_shared_xag.py`.

The search proved useful algebraically: degree/MD certificates, rank bounds,
relative-XAG quotient tests, and exact r=0/r=1/r=2/r=3 investigations narrowed
the possibilities. In particular, the prefix-relative r=3 tests for the
selected X44 and Y61 prefixes found no witness in their bounded quotient
families.

The failure was the same translation gap: a low multiplicative-depth witness
does not automatically provide a jointly shareable nine-wire reversible
schedule. The shared structured-XAG solver returned UNKNOWN at its short
limits, not UNSAT, and no candidate was promoted.

### 8. Fixed-label, free-label, class-relabel, and descriptor-code searches

Locations include `src/post190_class_relabel.py`,
`src/post190_structured_audit.py`, `src/post190_free_label_xag.py`,
`src/post190_mixed_descriptors.py`, `src/post190_extract_labels.py`,
`src/post190_sparse_degree_codes.py`, `src/post190_split_degree_codes.py`,
`src/post190_degree_rank_bound.py`, `src/post190_register_encoder.py`, and
`src/sub140_class_label_anneal.py`. Records include
`docs/POST190_CLASS_RELABEL_CAMPAIGN.md`, `docs/POST190_STRUCTURED_AUDIT.md`,
`docs/POST190_STRUCTURED_KERNEL.md`, `docs/POST190_STRUCTURED_SHARED_XAG.md`,
`docs/POST190_SUB137_CAMPAIGN.md`, and `docs/POST190_XAG_DEGREE_CERTIFICATE.md`.

What was tested:

- all normalized cuts of the 11 row/column equivalence classes;
- direct 4-bit labels for 11 classes and the older protected raw+class labels;
- mixed raw/class descriptors, split-degree codes, sparse degree codes, and
  affine-equivalent witnesses;
- care-set kernels on 121 or 182 reachable code pairs with don't-cares outside
  the reachable set;
- joint XAG sharing, encoder occupancy, register pressure, and kernel phase
  screens.

What failed:

- low-degree and low-AND label choices did not yield a strong jointly merged
  XAG advantage;
- structured shared-XAG searches were unresolved at their bounded solver
  limits;
- some kernel screens improved parity support but not complete native depth;
- no direct relabeling was promoted because it did not substantially beat the
  protected encoder/kernel trade-off.

This line answered the important architectural question partially: label
choice affects the kernel and encoder, but the tested direct relabelings did
not explain the large depth gap.

### 9. Phase-polynomial, phase-history, phase-retention, and phase-weaving work

Locations include `src/phase.py`, `src/phase_history_search.py`,
`src/phase_retention.py`, `src/phase_retention_affine.py`,
`src/phase_polynomial_aam.py`, `src/phase_rank_basis_search.py`,
`src/phase_rank_basis_anneal.py`, `src/post190_phase_weave_audit.py`,
`src/post190_window_phase.py`, `src/post188_phasepoly_probe.py`,
`src/post188_global_pauli.py`, `src/post188_loader_pauli.py`,
`src/post188_joint_phase_loader.py`, and `src/shared_y_phase*.py`.
Records include `docs/PHASE_HISTORY.md`, `docs/PHASE_RETENTION_REPORT.md`,
`docs/POST190_PHASE_WEAVE_CAMPAIGN.md`, `docs/POST188_PHASE_REORDERING.md`,
and `docs/POST190_NONLINEAR_AND_WINDOWS.md`.

What worked:

- phase-history rank and parity supports were measurable;
- phase-edge retention and integer full-turn phase representatives were exact;
- safe reordering/fusion contributed to historical 186/855 and related
  improvements;
- unreachable-state phase freedom was correctly treated as a don't-care only
  when the reachable phase ratio stayed exact.

Why it failed as a new architecture:

- target phase was not in the promising historical span in the original
  phase-history branch;
- phase-only proposals reached about 1345/1027 in one exact construction;
- phase-weaving and sparse-code methods reduced terms but increased loader or
  scheduling depth;
- kernel conjugation screens produced roughly 96–115-depth kernels, worse than
  the best fixed kernel;
- AAM numeric-angle handling required a local modulo-`2*pi` correction, and
  corrected constructions still measured roughly 256–268 kernel depth;
- fixed-boundary, local-window, context-scored, and CZ-orientation searches
  produced no sub-185 depth circuit.

### 10. Kernel synthesis, don't-cares, cofactor, SAT, and solver-guided methods

Locations include `src/post190_structured_kernel.py`,
`src/post190_kernel_rewrites.py`, `src/post190_kernel_seed_sweep.py`,
`src/post196_care_phase_lp.py`, `src/post196_care_tune.py`,
`src/post221_kernel_cofactor_cadical*.py`, `src/post221_kernel_degree*.py`,
`src/post221_kernel_cube_nulls.py`, `src/post221_kernel_signed_lift.py`,
`src/post221_kernel_cofactor_frames.py`, and `src/post224_reachable_kernel.py`.
Records include `docs/POST190_STRUCTURED_KERNEL.md`,
`docs/POST196_RESEARCH.md`, `docs/POST221_RESEARCH.md`,
`docs/POST224_REVIEW_AND_EXPERIMENTS.md`, and `docs/POST258_RESEARCH.md`.

Methods included sparse ANF completion, phase-support minimization, integer
phase lifts, reachable-state don't-cares, cofactor projection, degree SAT,
CaDiCaL, Z3, cardinality encodings, kernel rewrites, and randomized kernel
scheduling.

Successful pieces:

- reachable-care exactness was checked on 121, 182, or 256 combinations as
  appropriate;
- corrected CaDiCaL adapters expanded cardinality constraints and passed
  degree-five positive controls;
- the 258 family reduced a kernel from 107 to 88 layers and yielded a verified
  243-depth package;
- the later integer full-turn representation reduced the kernel from 69 to 66
  layers in the 218 family.

Failure modes and corrections:

- an early CNF adapter left pseudo-Boolean atoms unexpanded and produced an
  invalid SAT indication;
- an early direct adapter left bit-vector distinctness unexpanded;
- in-process Python timers could not stop native CaDiCaL reliably; future
  bounded runs must use `src/run_bounded.py`;
- degree-three/four UNSAT results apply only to specified fixed code frames,
  not arbitrary simultaneous recodings;
- kernel term count and degree were weak proxies for native depth;
- exact kernels with larger reachable code spaces often consumed the saved
  depth in the loader or in phase routing.

### 11. Five-variable loaders, address-width reductions, and in-place encoders

Locations include `src/post185_five_address.py`,
`src/post185_relabel_compile.py`, `src/post196_address_width.py`-style modules,
`src/post196_dirty_descriptor.py`, `src/post196_low_degree_codes.py`,
`src/post196_conditional_codes.py`, `src/post224_inplace_native.py`,
`src/post224_reachable_kernel.py`, `src/post258_raw_parity_codes.py`,
`src/post258_encoder_lifts.py`, and `src/post258_independent_codes.py`.
Records include `docs/POST185_FIVE_ADDRESS_AUDIT.md`,
`docs/POST185_LOADER_ADDRESS_WIDTH.md`, `docs/ADDRESS_WIDTH_CLOSURE.md`,
`docs/POST224_REVIEW_AND_EXPERIMENTS.md`, and `docs/POST258_RESEARCH.md`.

The five-variable route found real 60-layer loaders and verified multiple
complete oracles, but the larger kernels dominated: the best follow-up was
about 265/911 and a comparable initial witness was 307/1002. Both-axis
compression helped within the family but remained worse than 185.

In-place code wires, nonlinear tags, raw parity codes, and independent codebooks
were also exact in selected mappings, but compiled complete circuits were much
deeper (for example, 388–480-depth constructions). The key failure was moving
work from the loader into a kernel without reducing the total reversible
critical path.

### 12. Quotient permutations, coordinate preconditioning, and QFT/arithmetic

Locations include `src/quotient_permutation.py`, `src/post190_y_fold.py`,
`src/post190_y_fold_audit.py`, `src/post190_radius_interval.py`,
`src/post190_radius_carry.py`, `src/qft_recenter.py`, `src/inplace_d4.py`,
`src/inplace_subspace.py`, and related arithmetic modules. Records include
`docs/QUOTIENT_PERMUTATION.md`, `docs/POST190_Y_FOLD_AUDIT.md`,
`docs/POST190_Y_FOLD_COST.md`, `docs/ARITHMETIC_MIDDLE_PROBE.md`, and
`docs/POST190_ARITHMETIC_SCHEDULE.md`.

These methods exploited the 11-by-11 quotient structure, nested class geometry,
coordinate shifts, and possible in-place relabeling. They produced useful
structural diagnostics, but central dyadic phase diagnostics reached roughly
5877/4682 and arithmetic folds/ripples were too expensive. No reversible
coordinate preconditioner showed a credible native depth advantage.

### 13. BDD, cofactor, LUT/ESOP, and semantic-window synthesis

Locations include `src/bdd_cofactor_mine.py`, `src/bdd_cofactor_score.py`,
`src/bdd_reversible.py`, `src/bdd_dirty_reversible.py`, `src/lut_decomposition.py`,
`src/lut_mux_oracle.py`, `src/lut_single_target.py`, `src/cofactor_full_oracle.py`,
`src/cofactor_product_phase.py`, `src/semantic_window.py`,
`src/window_profile.py`, `src/dag_window_resynthesis.py`,
`src/strict_window_pilot.py`, and `src/local_esop_order_search.py`.
Records include `docs/LUT_SINGLE_TARGET.md`, `docs/RESEARCH_CLOSURE_2026-09-11.md`,
`docs/DEPTH_GAP_ANALYSIS_2026-09-12.md`, and `docs/TWO_HOUR_CLOSURE_REPORT.md`.

BDD cofactors, LUT mappings, dirty-target single-target gates, ESOP covers,
semantic windows, and local DAG resynthesis were all useful exact classical or
local compiler tools. They failed to become a sub-185 full oracle because:

- LUT/BDD compactness did not survive reversible embedding;
- dirty-target restoration and relative phase added substantial overhead;
- the best optimistic single-target forward critical path was about 145 depth
  before complete oracle composition;
- window-local improvements could not overcome the surrounding loader and
  uncompute barriers.

### 14. MPO, TT, tensor, QBP, ZH, and direct unitary/state-space approaches

Locations include `src/mpo_*.py`, `src/tt_unitary/`, `src/qbp/`,
`src/nie_zi_finite.py`, `src/nonabelian_branch_search.py`,
`src/nonabelian_z3_synth.py`, `src/unitary_state_space`-related modules,
`src/tensor_rank_exact.py`, and `src/zh_direct/`. Records include
`docs/MPO_NATIVE_SYNTHESIS.md`, `docs/UNITARY_STATE_SPACE.md`,
`docs/NONLINEAR_SPECTRAL.md`, and `docs/RESEARCH_REVIEW_2026-09-09.md`.

The exact tensor/MPO/TT representations were validated, and bounded QBP,
finite-size, ZH, Procrustes, Riemannian, Adam, bus, and non-chain optimizer
probes were run. The failure was objective-to-circuit translation:

- generic unitary optimizers plateaued or optimized the wrong representation;
- width-4 and continuous QBP probes did not yield a useful exact reversible
  circuit;
- MPO/TT compression did not include the native width, ancilla restoration,
  phase, and `u3`/`cx` constraints needed for the score;
- no result passed the promotion gate as a verified improvement.

### 15. CNOT rewrites, phase reordering, commutation, scheduling, and compiler stacks

Locations include `src/post185_cz_orientation.py`,
`src/post185_phase_placement.py`, `src/post185_sat_phase_blocks.py`,
`src/post185_solver_walk.py`, `src/post185_timed_local.py`,
`src/post186_cnot_bridge.py`, `src/post186_context_windows.py`,
`src/post186_exact_local_phase.py`, `src/post186_split_schedule.py`,
`src/post188_global_pauli.py`, `src/post188_phasepoly_probe.py`,
`src/post190_commuting_schedule.py`, `src/post190_exact_schedule.py`,
`src/post193_endpoint_grid.py`, `src/post193_endpoint_beam.py`,
`src/current_critical_path.py`, `src/pytket_peephole_oracle.py`,
`src/tket_global_optimize.py`, and `src/tket_phase_history_optimize.py`.
Records include `docs/POST185_DEPTH_CAMPAIGN.md`,
`docs/POST186_CNOT_REWRITES.md`, `docs/POST188_PHASE_REORDERING.md`,
`docs/POST190_COMMUTING_SCHEDULE.md`, `docs/POST193_RESEARCH.md`,
`docs/POST193_ENDPOINT_GRID.md`, and `docs/POST193_CX_REFINEMENT.md`.

This was the most productive late-stage optimization family:

- local CNOT identity rewrites and exact scheduling established 185/854;
- phase reordering/fusion produced 186/855 and related historical circuits;
- endpoint grids, boundary choices, commuting DAGs, and compiler replay
  produced 188–193 depth variants and a 193/853 CX tie-breaker;
- Pytket/Tket peepholes sometimes reduced CX but not primary depth.

Why it did not reach the external leader:

- fixed gate multisets hit per-wire occupancy and critical-path floors;
- neutral proxy changes were not native depth gains;
- allowing more CX did not expose a depth reduction in the tested fixed
  architecture;
- several local solver probes ended in UNKNOWN or timeout;
- CNOT savings became a distraction once the user prioritized depth.

The current steering is therefore depth-first: do not spend future rounds on
CX tie-breaks unless depth also improves.

## Repeated correctness and engineering failures caught

The repository contains several important corrections that explain why raw
search numbers cannot be trusted without replay:

1. Qiskit transpilation of oracle/reusable subcircuits must use
   `qubits_initially_zero=False`; the default produced invalid low-depth results.
2. Nonidentity transpiler layouts must be materialized before QASM serialization
   or subcircuit composition; layout metadata is not a gate.
3. Relative-phase gates need coherent compute/phase/uncompute justification.
4. `Ry(pi) = -iY`, not `-iX`; omitting the state-dependent phase invalidates a
   loader replacement.
5. A phase synthesis wrapper initially used modulo `pi` instead of `2*pi`.
6. A SAT adapter initially failed to expand pseudo-Boolean/cardinality atoms.
7. Direct bit-vector distinctness required explicit expansion.
8. In-process timers do not reliably interrupt native CaDiCaL; use an external
   bounded process.
9. Historical reports must be SHA-matched to the actual QASM and may not be
   reused after overwriting a candidate.
10. The latest whole-schedule pilot initially counted CX as a three-wire gate;
    that accounting was corrected and tested.

These were not cosmetic issues: each could create a false depth improvement,
false SAT result, or false verification claim.

## Cross-cutting lessons

### Classical cost is not native depth

AND count, algebraic degree, Walsh support, LUT count, phase-term count, and
MPO rank are useful screens, but none includes live-register pressure,
uncomputation, phase cancellation, routing, wire occupancy, or the exact
transpiler basis. Every promising proxy eventually needed native compilation.

### The real bottleneck is coordinated reversible information flow

The logo has only 11 row and 11 column classes, but class information must be
loaded, used in a diagonal phase operation, and restored with six clean
ancillas. Methods that optimize only a loader, only a kernel, or only a phase
polynomial usually move the cost to another stage.

### Don't-cares help, but only on reachable states

The 121/182-care kernel formulations and unreachable-state phase screens were
legitimate and sometimes materially useful. They did not justify arbitrary
labels or phase changes on states reachable through relative phases.

### Exact verification is a promotion gate, not a final formality

The best historical local improvements were found only after exact-file replay,
QMOD gate matching, dense checks, and exhaustive verification. Approximate
classifiers and stale metadata are research evidence, not submissions.

## What remains open

The following are not proven impossible:

- an entirely new operator-level architecture;
- a width-aware direct reversible synthesis method that jointly optimizes
  loader, phase, and uncompute;
- arbitrary simultaneous class recodings outside the fixed SAT frames;
- a new native circuit explaining the external 137-depth leader.

The following should not be reopened without new evidence:

- more ordinary AND-count/XAG factoring;
- more fixed-gate CNOT tie-breaker sweeps;
- phase-term minimization without a native depth model;
- generic MPO/TT optimizer tuning;
- old label implementations under a different compiler seed;
- the closed whole-schedule pilot without a materially different move set or
  architectural invariant.

## Source and documentation coverage

The audit covered the Markdown research record in `docs/`, package READMEs in
`artifacts/*/README.md`, and source/test inventories under `src/` and `tests/`.
The main index documents are `docs/METHOD_INDEX.md`, `docs/EXPERIMENTS.md`,
`docs/HANDOFF.md`, and `docs/CURRENT_DESIGN.md`; campaign-specific findings are
cross-referenced above. The source inventory is intentionally grouped by
method family because many modules are successive variants of the same
experiment rather than independent algorithms.

The remaining README and campaign records are covered as follows:

- baseline and package records: `README.md`, `artifacts/185/README.md`,
  `artifacts/186/README.md`, `artifacts/188/README.md`, `artifacts/193/README.md`,
  `artifacts/193_cx853/README.md`, `artifacts/196/README.md`,
  `artifacts/198/README.md`, `artifacts/218/README.md`, `artifacts/221/README.md`,
  `artifacts/222/README.md`, `artifacts/224/README.md`, `artifacts/226/README.md`,
  `artifacts/243/README.md`, `artifacts/243_cx951/README.md`,
  `artifacts/258/README.md`, `artifacts/531/README.md`;
- structural and early research: `CLASSICAL_STRUCTURE.md`,
  `COMPARATOR_ORACLE.md`, `FOLD_THEN_LOOKUP.md`, `LEVEL_COMPARATOR.md`,
  `MINMC_RANK_REPORT.md`, `NONLINEAR_LOADER_PROBE.md`,
  `NONLINEAR_SPECTRAL.md`, `QUOTIENT_PERMUTATION.md`, `UNITARY_STATE_SPACE.md`;
- closure and review: `DEPTH_GAP_ANALYSIS_2026-09-12.md`,
  `REASSESSMENT_2026-09-09.md`, `RESEARCH_REVIEW_2026-09-09.md`,
  `RESEARCH_CLOSURE_2026-09-11.md`, `SUB180_REASSESSMENT_2026-09-12.md`,
  `TWO_HOUR_CLOSURE_REPORT.md`, `V2_NATIVE_CHECKPOINT_2026-09-12.md`;
- post-185 through post-190 campaigns: all `POST185_*`, `POST186_*`,
  `POST188_*`, and `POST190_*` records, including the class-relabel,
  information-space, joint-stage, register, side-analysis, sink, structured,
  phase-weave, relative-XAG, Y-fold, and whole-schedule reports;
- post-193 through post-258 campaigns: `POST193_*`, `POST196_*`,
  `POST218_RESEARCH.md`, `POST221_RESEARCH.md`,
  `POST224_REVIEW_AND_EXPERIMENTS.md`, `POST258_RESEARCH.md`,
  `DISTRIBUTED_LOOKUP_258.md`, `VECTOR_LOADER_REPORT.md`, and `THREE_SWEEP.md`;
- operational prompts and reports: `OVERNIGHT_AGENT_PROMPT.md`,
  `OVERNIGHT_REPORT.md`, `METHOD_INDEX.md`, `HANDOFF.md`, and `EXPERIMENTS.md`.

This file is a synthesis of the records, not a replacement for their raw
artifacts. When a number or status conflicts, the current handoff, the actual
serialized QASM, its SHA-matched verification report, and the current
`AGENTS.md` control.
