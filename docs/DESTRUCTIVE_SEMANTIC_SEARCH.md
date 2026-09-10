# Destructive Semantic Search

## Status

This is the first implementation of the destructive-classifier search. It is
separate from the protected 524-depth artifact and from the input-preserving
v0 baseline.

The search represents every physical wire by a 4096-bit Boolean truth table
over the original x/y coordinate domain. The six ancillas initially contain
zero. A destructive RCCX update is represented as

```text
W[target] <- W[target] XOR (W[a] AND W[b])
```

The physical input wires may be targets. Reversibility is supplied by the
underlying monomial gate and its exact inverse, not by keeping the original
coordinate function visible.

## Search model

`src/destructive_semantic_search.py` currently provides:

- exact input and logo truth tables;
- semantic X, CX, and RCCX updates;
- affine GF(2) span detection for the logo target;
- configurable constant/single/pair or order-3 residual heuristics;
- deterministic bounded beam search over RCCX updates;
- reversible X/CX affine completion when the target enters the span;
- checkpoint serialization under `artifacts/destructive_semantic/checkpoints/`.

`src/verify_destructive_classifier.py` replays a saved gate history over the
same semantic engine and checks all 4,096 inputs before any quantum oracle is
constructed.

## Initial validation sequence

The first runs are intentionally small: primitive semantics, target cardinality,
toy span cases, then beam widths 32–64 and two to four nonlinear layers. The
preserve-inputs flag is an ablation; it is not the target architecture.

The main target is affine completion at low forward depth. A forward depth at
or below 110 is promising; at or below 94 gives a nominal `2d+1 < 190`
conjugated-oracle budget before global compiler cancellation.

The native primitive calibration measured one RCCX at depth 7 and 3 CX in the
current U3/CX basis; two disjoint RCCXs also occupy depth 7. The search uses
that calibrated depth as its heuristic cost.

## Verification boundary

An affine-completed classifier is not yet a valid competition oracle. For every
promising classifier, construct `C^dagger Z C`, serialize the complete circuit
in `u3`/`cx` with `qubits_initially_zero=False`, and run the repository's
exhaustive phase/leakage verifier. The protected files under `artifacts/524/`
must remain unchanged.

## Limitations of the first implementation

The initial beam uses single RCCX transitions and an affine residual proxy. It
does not yet perform guided rank/XAG seed construction or a complete native
cost model. Disjoint layer generation and native-cost calibration are now
implemented; exact meet-in-the-middle distance is reported for the selected
final state but is not used to rank every child.

## Observed result

Primitive tests passed, including the 1,097-state target cardinality and toy
affine-span cases. A beam-128 run with 48 proposals per state reached layer 13
before the next expansion exceeded the current memory budget. The best saved
state had residual 501 and estimated forward depth 36, and its gate history
used original coordinate wires as RCCX targets. This is evidence that the
destructive semantics are active, not a complete classifier or oracle.

The matching preserve-inputs ablation reached residual 575, versus residual
473 for the calibrated destructive run. This confirms a measurable benefit from
allowing coordinate wires to be overwritten. Neither run reached affine
completion.

The disjoint-RCCX layer extension was validated, but a beam-128 run with two
RCCXs allowed per layer reached residual 575 by layer 9 before memory pressure.
A lower-fanout single-RCCX run reached residual 503 by layer 25 at estimated
depth 126. These results motivate exact selected-state affine-distance scoring
and guided semantic proposals rather than simply increasing the beam.

Exact meet-in-the-middle distance was then enabled for the leading 16 children
per layer. It matched the proxy-selected trajectory through the observed layer
9 boundary and added substantial runtime without producing a lower residual.
It is retained as an optional diagnostic; broad exact ranking is not currently
cost-effective.

An all-child exact-ranking control run (beam 32, eight proposals, eight
layers requested) was also negative: it remained at residual 971 by layer 2
and hit the resource boundary, while the cheaper proxy trajectory reached 827
at that point. Exact span distance is therefore retained for final-state
diagnostics, not used as the primary beam objective.

Affine-control RCCX sandwiches were also tested. The macro
`CX(c,a); RCCX(a,b,t); CX(c,a)` is semantically reversible and exposes
`(W[a] XOR W[c]) AND W[b]`. A beam-64, 16-proposal, ten-layer run reached
residual 609 at estimated depth 51, worse than the plain destructive run's
residual 539 at a comparable layer budget. The macro is retained as an
available primitive, but this proposal ranking is not currently competitive.

Seed diversity was screened separately. With beam 64 and 24 proposals, seed 1
reached residual 487 and seed 94 reached 499 after 16 layers; the stronger
beam-128 seed-1 run reached residual 553 by layer 9 before memory pressure.
Neither beat the seed-524 residual 473 trajectory. Simple tie-breaking seed
variation is therefore not the next lever.

An optional order-3 residual proxy was added, considering affine combinations
of up to three current wires. Beam 64 with 16 proposals reached residual 531 by
layer 10 and residual 513 by layer 14 at estimated depth 84, improving on the
order-2 residual 539 at the comparable ten-layer point. Increasing the proposal
limit to 24 reproduced residual 531 by layer 10 without a further gain. This
is the best current heuristic variant, but it remains far from affine
completion.

A full-proxy proposal mode was added as a controlled experiment. It first
keeps a bounded shortlist using the cheap direct/pair hint, then scores that
shortlist with the complete configured proxy. This avoids evaluating every
legal RCCX mutation while retaining some order-3 guidance. The mode remains
behind `--full-proxy-proposals`; it is an exploratory ranking control rather
than a replacement for the default beam.

The search also supports a two-sided affine-control block behind
`--biaffine-controls`:

```text
CX(mix_a, a); CX(mix_b, b); RCCX(a, b, target);
CX(mix_b, b); CX(mix_a, a)
```

Its semantic update is
`W[target] ^= (W[a] XOR W[mix_a]) AND (W[b] XOR W[mix_b])`, with all five
wires distinct. The block is reversible and its semantic replay was checked
against the decomposed CX/RCCX sequence. A beam-16, six-layer, order-3 run
reached residual 647 at estimated depth 41; the selected six-block history
compiled to forward depth 35 and 30 CX gates. This is an improvement over the
early plain trajectory but still does not approach affine completion, and the
proposal enumeration is expensive. Compact evidence is in
`artifacts/destructive_semantic/biaffine_b16x6_p4.metrics.json`.

Finally, bounded two-RCCX lookahead was added behind `--double-rccx`. Each
search move contains two serial plain RCCXs, and the pair is scored after both
updates. This lets the beam retain synergistic pairs whose first mutation is
not individually attractive. A beam-16, six-layer, order-3 run reached
residual 593 after 12 RCCXs at estimated depth 77; the selected history
compiled to forward depth 59 and 34 CX gates. This is the best current
destructive-search heuristic result, but it still has no affine completion.
Compact evidence is in
`artifacts/destructive_semantic/double_b16x6_p4.metrics.json`.

The layer-6 checkpoint was resumed to layer 10 with the same deterministic
configuration. The best state improved to exact affine residual 581 at layer 9
(18 RCCXs in its retained history); its serialized forward circuit measured
depth 88 and 52 CX gates. This crosses the nominal forward-depth screening
threshold, but it is not a classifier: its best affine-span residual is 581,
and no phase oracle was constructed or verified. Direct replay of the selected
physical target is a separate check performed by the classifier verifier.
Evidence is in `artifacts/destructive_semantic/double_resume_b16x10_p4.metrics.json`.

The optional `--pareto-beam` selector now retains residual/depth
non-dominated states before filling the beam by the normal score. This is the
requested schedulability safeguard: a state can survive because it is
shallower even when its residual is slightly worse. On the beam-16,
double-RCCX layer-10 control it reproduced residual 581 and compiled depth 88,
with no improvement for seed 524. Evidence is in
`artifacts/destructive_semantic/double_pareto_b16x10_p4.metrics.json`.

Seed diversity was then applied to the stronger double-RCCX move set. Seed 1
reached residual 447 at layer 6 and residual 429 at layer 10. The retained
20-RCCX history compiled to forward depth 92 and 58 CX gates; extending it to
layer 14 did not lower the residual. This is the current best heuristic result
and falls inside the nominal depth-94 screening range, but it remains
incomplete: its best affine-span residual is 429 and no conjugated oracle was
built or verified. Evidence is in
`artifacts/destructive_semantic/double_seed1_b16x10_p4.metrics.json`.

The same seed-1 beam also retained a depth-favorable Pareto state with
residual 383. Its standalone compiled forward circuit measured depth 91 and
58 CX gates, making it preferable for depth screening to the residual-379
state at depth 112. The complete gate history and semantic hash are preserved
in `artifacts/destructive_semantic/double_seed1_b32x10_p4_pareto_depth91.json`.

Guided semantic proposals are available behind `--guided-hints`. The loader
converts 30 existing x/y rank-factor truth tables into 12-variable truth-table
hints; these only affect proposal ordering and never constrain a physical wire
to a named feature. A guided double-lookahead continuation reached residual
581, matching the non-guided search, but compiled to depth 99 and 58 CX gates
versus the shallower depth-88 control. The hints are therefore useful for
diversity but not currently the preferred depth objective. Evidence is in
`artifacts/destructive_semantic/guided_double_b16x10_p4.metrics.json`.

The seed-94 control did not approach seed 1 in residual, but it produced the
shallowest measured point so far: affine residual 531 at compiled depth 81 and
48 CX gates. It is retained as a shallow Pareto candidate, not as a
classifier. Its exact gate history is in
`artifacts/destructive_semantic/double_seed94_b32x8_p4_depth81.json`.

Parallel seed screening found a stronger shallow point with seed 42: affine
residual 447 at compiled forward depth 59 and 32 CX gates. This dominates the
seed-94 depth-81/residual-531 point and is a new shallow Pareto candidate, but
it remains an affine approximation rather than a verified classifier. Its
exact history is in
`artifacts/destructive_semantic/double_seed42_b16x6_p4_depth59.json`.

Resuming seed 42 through layer 10 lowered the affine residual to 423. The
18-RCCX history compiled to forward depth 73 and 46 CX gates, producing a
second strong Pareto point between the depth-59/residual-447 and
depth-84/residual-379 candidates. Its history is preserved in
`artifacts/destructive_semantic/double_seed42_b16x10_p4_depth73.json`.

Continuing seed 42 through layer 14 lowered the affine residual to 415. The
26-RCCX history compiled to forward depth 97 and 66 CX gates, giving a
lower-residual but deeper point than the depth-73/residual-423 candidate. It
is preserved in
`artifacts/destructive_semantic/double_seed42_b16x14_p4_depth97.json`.

An optional `--forward-affine-controls` move now explores the destructive
prefix `CX(mix_a,a); CX(mix_b,b); RCCX(a,b,t)` without restoring the controls.
Its semantic implementation was checked against the decomposed sequence, and
it obeys the all-wires-writable model. A seed-1 beam-16 four-layer control
reached affine residual 647 at compiled depth 26 and 15 CX gates, so this move
was not competitive in the short test. It remains available for mixed future
searches. Evidence is in
`artifacts/destructive_semantic/forward_affine_b16x4_p4.metrics.json`.

Bounded three-RCCX lookahead is available behind `--triple-rccx`. It uses a
staged proposal pool and scores the state after all three reversible updates.
The cold seed-1 beam-16, three-layer control reached affine residual 575 at
compiled depth 53 and 27 CX gates, weaker than the established double-RCCX
basin. A separate local three-step probe around the residual-359 state found
residual 355, so the move is retained as an optional escape mechanism rather
than the default search. Evidence for the cold control is in
`artifacts/destructive_semantic/triple_seed1_b16x3_p4.metrics.json`.

The triple move was then resumed from the preserved seed-1 residual-359 state
and reproduced the local improvement to residual 355 with the three-gate
extension `(1,12,11); (1,17,12); (2,12,11)`. Its serialized circuit measured
depth 125 and 65 CX gates, so it is a lower-residual but deeper frontier point.
The compact continuation record is in
`artifacts/destructive_semantic/double_seed1_targeted_triple_residual355.json`.

A further targeted continuation reduced the exact affine residual to 349. The
29-RCCX history compiled to forward depth 149 and 83 CX gates, with affine
combination `(11,17)`. This is lower residual but materially deeper than the
residual-359/depth-107 frontier point, and direct target-wire replay still had
1057 mismatches. It is recorded in
`artifacts/destructive_semantic/targeted_triple_residual349.json` and is not a
complete classifier or phase oracle.

A divergent continuation seeded directly from the residual-349 state (beam 16,
four double-RCCX layers, Pareto retention, exact scoring on eight leaders)
also remained at residual 349. This rules out a simple greedy-path artifact in
that local window; the negative result is preserved in
`artifacts/destructive_semantic/residual349_double_beam4.metrics.json`.

A four-layer forward-affine-control continuation from the same state also
remained at residual 349, despite Pareto retention and exact scoring of eight
leaders. Its metrics are preserved in
`artifacts/destructive_semantic/residual349_forward_affine4.metrics.json`.

The objective was then changed to direct target-wire mismatch, without using
affine-span residual for selection. A 32-state, 12-layer RCCX beam reached 609
mismatches on q11 at estimated depth 70, weaker than the residual-349 affine
frontier. This confirms that direct-wire targeting is a distinct trajectory;
its gate history is preserved in
`artifacts/destructive_semantic/direct_wire_beam_seed1919.metrics.json`.
The same objective is now reproducible with the search engine's
`--direct-target` option; affine-span ranking remains the default.

A deeper direct-target run (seed 2024, beam 32, 20 layers) improved the best
direct mismatch to 543 on q11. Its 26-RCCX history compiled to forward depth
60 and 62 CX gates, but it remains incomplete. The exact record is in
`artifacts/destructive_semantic/direct_wire_beam_seed2024.metrics.json`.

Extending that exact history with a targeted 12-layer beam reduced the direct
q11 mismatch further to 513. The resulting 44-RCCX circuit compiled to forward
depth 113 and 106 CX gates. It remains incomplete; its full history is in
`artifacts/destructive_semantic/direct_wire_seed2024_extended.metrics.json`.

A further continuation reduced the mismatch to 501 on q11. The 56-RCCX
candidate compiled to forward depth 155 and 128 CX gates; the last three-gate
continuation then plateaued. Its compact extension record is in
`artifacts/destructive_semantic/direct_wire_seed2024_residual501.metrics.json`.

As a correctness baseline, the existing input-preserving v0 oracle was also
run through exhaustive verification on all 4,096 clean-ancilla basis inputs.
It passed with SHA-256
`4f684dd7aea6173236d6fea6e16bbfd4e26c198ad932c8b90ccc602d636e3e38`, depth
21,392, and 15,462 CX gates. The copied report is
`artifacts/destructive_semantic/v0_oracle_exhaustive.metrics.json`; this does
not validate any incomplete destructive-search candidate.

An exact row-factor classifier baseline was then constructed from ten row
terms using no-ancilla MCX predicate synthesis. Its forward classifier
compiled to depth 6,531 / 3,739 CX, and its conjugated oracle compiled to
depth 13,064 / 7,476 CX. The serialized oracle passed exhaustive verification
on all 4,096 inputs with zero ancilla leakage. The QASM and matching metrics
are in `artifacts/destructive_semantic/row_factor_classifier.qasm`,
`artifacts/destructive_semantic/row_factor_oracle.qasm`, and
`artifacts/destructive_semantic/row_factor_verified.metrics.json`. This is an
exact correctness baseline, not a destructive-search result.

An exact dirty-ancilla ESOP control was also tested as a concrete destructive
embedding: the classifier computes the logo into q12, permits dirty-chain
workspace, and swaps q12 with q11 so the required midpoint wire is q11 while
the old q11 value becomes garbage. Exhaustive verification passed on all 4,096
inputs, but the serialized oracle measured depth 21,412 / 15,462 CX, slightly
worse than the v0 oracle. Its verified measurements are recorded in
`artifacts/destructive_semantic/dirty_esop_exact_control.metrics.json`; this
is a correctness control, not an optimization result.

A direct-target triple-RCCX control was also run from seed 2024 (beam 16,
four layers, proposal limit 4). It reached 589 mismatches on its best
physical wire at estimated depth 63 after 12 RCCXs. This is weaker than the
existing direct-target residual-501 frontier and remains an incomplete
classifier; its exact history is recorded in
`artifacts/destructive_semantic/direct_triple_seed2024_b16x4_p4.metrics.json`.

Higher-order primitive screening was also performed from the corrected
direct-target residual-501 state. An exhaustive one-step scan of all 9,780
legal three-control-X updates found no direct-target or affine-residual
improvement: the best result remained 501 mismatches. The scan is recorded in
`artifacts/destructive_semantic/mcx3_residual501_one_step.metrics.json`; a
larger order-3 beam was stopped after its scoring cost grew without producing
a better state.

An exact algebraic completion test was then applied to the direct-501 and
affine residual-359/355/349 frontier states. For every physical target wire,
the remaining correction was tested against the GF(2) span of the constant,
all current wires, all pair-products, and all cubic products. No completion
exists in any of those 18 x 4 cases. The negative structural result is in
`artifacts/destructive_semantic/frontier_cubic_completion.metrics.json`.

The direct-target residual-501 state was then tested to product degree 7 for
all 18 possible target wires. No correction was found in the GF(2) span of
the constant and all products of up to seven distinct other current wires.
This rules out a low-order multiplicative tail for that state; the exact
negative result is recorded in
`artifacts/destructive_semantic/direct501_product_span_degree7.metrics.json`.

The remaining mixed affine move-set control was screened with affine,
biaffine, and unrestored forward-affine proposals enabled together (seed 1,
beam 16, proposal limit 4, order-3 proxy). It reached residuals 827, 759,
and 653 through three completed layers, remaining weaker than the existing
frontiers; layer 4 was stopped during expensive proposal scoring. The bounded
result is recorded in
`artifacts/destructive_semantic/mixed_affine_seed1_b16x4_p4.metrics.json`.

The separate non-Abelian phase-computer direction now has a finite-group
prototype in `src/nonabelian_branch_search.py`. It constructs and checks the
120-element binary icosahedral multiplication table, then evaluates a
width-2 branching program over all 4,096 inputs using only table lookups. An
initial stochastic length-16 control reached 3,796 mismatches, so it is not a
candidate oracle and no QASM was generated. The result is preserved as
`artifacts/destructive_semantic/nonabelian_l16_initial.metrics.json`; the
prototype remains a research direction rather than a correctness result.

The non-Abelian direction now also has a Z3 hard-constraint probe in
`src/nonabelian_z3_synth.py`. A four-instruction one-pass schedule over bits
0--3 was proven unsatisfiable in 1.411 seconds. The full 12-instruction
schedule under the residual-oriented variable order reached the 60-second
solver timeout, so it is recorded as unknown rather than treated as an
impossibility result. Measurements are in
`artifacts/destructive_semantic/nonabelian_z3_bounded.metrics.json`.

The target was also converted into an exact layered residual-function
branching program using variable order
`q0,q1,q2,q3,q4,q5,q11,q8,q6,q7,q9,q10`. The layer state counts are
`1,2,4,8,13,15,11,12,19,19,10,4,2`, with 1,097 marked inputs and a maximum
of 19 distinct residual functions. This is a structural diagnostic rather
than a reversible circuit: residual states can merge, so a future destructive
embedding must carry enough garbage to make each transition injective. The
reproducible extractor is `src/residual_branching_program.py`, with compact
measurements in
`artifacts/destructive_semantic/residual_branching_program_ordered.metrics.json`.

A first reversible embedding of that DAG stored each layer's residual-state
ID in five wires and synthesized the Boolean difference for every state bit
directly from the consumed prefix. The semantic construction was exact, but
its 589 ESOP terms compiled to forward depth 47,885 / 29,642 CX. This rejects
the naive prefix-ESOP embedding as an optimization path; the residual DAG is
still useful as a structural target for a transition synthesis that exploits
state-local controls. Measurements are in
`artifacts/destructive_semantic/residual_state_code_naive.metrics.json`.

Transition analysis shows why a local overwrite needs explicit garbage: the
maximum fixed-bit fan-in by layer is
`1,1,1,2,4,9,6,3,2,4,4,2`, requiring up to four distinguishing garbage bits
for an injective local embedding. These exact counts are in
`artifacts/destructive_semantic/residual_transition_fanin.metrics.json` and
rule out the simpler one-consumed-bit transition construction.

A 1,000-order random structural search, using the corrected extractor, found
the order `q10,q9,q7,q11,q5,q8,q6,q0,q1,q2,q4,q3`. It keeps the maximum
residual width at 19 while reducing maximum fixed-bit fan-in from 9 to 5 and
the peak distinguishing-garbage requirement from four bits to three. This is
an improved target for the future local-permutation synthesis, not yet a
classifier circuit. Measurements are in
`artifacts/destructive_semantic/residual_order_search.metrics.json`.

A second local search optimized the reversible slot recurrence rather than
fan-in alone. Its best order is
`q10,q5,q11,q4,q9,q8,q3,q1,q0,q2,q7,q6`, with layer residual widths
`1,2,4,7,12,16,21,29,35,23,6,4,2` and a peak of 85 tagged internal slots.
The corresponding minimum slot counts are
`1,2,4,7,13,20,31,45,63,73,77,81,85`. This is below the previous 216-slot estimate but still above the 64 states
provided by six clean ancillas, so it is a structural bound and not yet a
classifier implementation.

Using two history wires in addition to the six freed input wires gives an
8-bit reversible branching register. For the order
`q10,q5,q11,q4,q9,q8,q3,q1,q0,q2,q7,q6`, the first six inputs load 64 distinct
states; the remaining six controlled transitions require at most 126 tagged
states, within the 256-state capacity. The final residual slots can be
assigned output-bit parity 0/1 (77/49 slots), so this is an exact semantic
embedding model. A straightforward permutation completion has 554 adjacent
state transpositions before native decomposition, and no QASM has yet been
claimed. Measurements are in
`artifacts/destructive_semantic/reversible_width256_slot_machine.metrics.json`.

A fresh cold seed-42 triple-RCCX beam (16 states, four layers, proposal limit
4) reached exact residual 531 at estimated depth 77 after about 773 seconds.
It did not reach affine completion and is weaker than the targeted seed-1
basin. Its exact gate history and metrics are preserved in
`artifacts/destructive_semantic/triple_seed42_b16x4_p4.metrics.json`.

A wider seed-1 beam (64 states) found a stronger depth-screening point at
residual 403. Its 16-RCCX history compiled to forward depth 90 and 46 CX
gates, improving the depth-91 Pareto point while reducing CX count. The
the affine-span residual is 403, so this remains a heuristic candidate only.
Direct target-wire replay is separately recorded by the verifier. Its exact
gate history and semantic hash are preserved in
`artifacts/destructive_semantic/double_seed1_b64x8_p4_depth90.json`.

Resuming the beam-64 seed-1 checkpoint for one additional layer produced a
stronger candidate: residual 379 with compiled forward depth 84 and 48 CX
gates. This dominates the earlier depth-90 point while retaining the same
residual quality. Its affine-span residual is 379, while direct target-wire
replay still fails, so this is not yet a classifier or phase oracle. Its exact
gate history is preserved in
`artifacts/destructive_semantic/double_seed1_b64x9_p4_depth84.json`.

One further layer of the same beam reduced the residual to 359. The
residual-first 20-RCCX history compiled to depth 107 and 56 CX gates, so it is
not a replacement for the shallow depth-84/residual-379 point; together they
form the current measured Pareto frontier. The residual-359 history is
preserved in `artifacts/destructive_semantic/double_seed1_b64x10_p4_residual359.json`.

## Width-256 reversible embedding experiment

The residual-DAG analysis showed that a six-clean-ancilla state machine is too
narrow: the best reversible-slot recurrence peaks at 85 slots. A new semantic
model therefore loads the first six variables of the slot-oriented order
`(10,5,11,4,9,8)` into six clean ancillas and uses an eight-bit state register
of capacity 256. The remaining controls are `(3,1,0,2,7,6)`. The exact model
is implemented in `src/reversible_width256_synthesis.py`.

The model constructs six pairs of full 256-state permutations, with the
permutation selected by the next input bit. It assigns labels to preserve
identity where possible and, on the final layer, forces the least-significant
state-label bit to equal the terminal residual value. An exhaustive semantic
replay covers all 4,096 coordinate assignments and confirms the 1,097 marked
states. The compact measurements are in
`artifacts/destructive_semantic/reversible_width256_synthesis.metrics.json`.

This is a correctness-verified embedding, not a competitive oracle candidate.
The parity constraint and full-permutation completion require 538 adjacent
state transpositions, estimated as 3,488 Gray-path MCTs before decomposition
to U3/CX. That native cost is presently far beyond the target, so this model
is retained as a structural control and not promoted to a complete QASM
candidate. Native synthesis or a different state-labeling/decomposition
strategy remains pending.

## Width-128 state-machine control

The slot peak is a capacity bound, not an output-bit bound. A seven-bit state
register is sufficient for the transition history when the output is kept on
a separate clean wire, but it cannot encode the terminal 77/49 split as one
state parity bit. I therefore evaluated the terminal residual as a separate
seven-input Boolean function instead.

A 301-order neighborhood screen found the better order
`q10,q9,q11,q4,q5,q2,q3,q1,q0,q8,q7,q6`. Its exact seven-bit state machine
replays all 4,096 inputs, uses a peak of 99 slots, and costs 2,066 estimated
Gray-path MCTs. The terminal function has 45 ANF terms of degree six; its
standalone U3/CX compilation is depth 2,095 / 1,197 CX. These figures remain
far above the target, but they improve the prior width-128 control and provide
strong evidence that arbitrary permutation completion is the current
bottleneck. Measurements are in
`artifacts/destructive_semantic/reversible_width128_order_search.metrics.json`.

Affine state relabeling was screened as a low-cost way to simplify those
transitions. XOR offsets at the layer boundaries retained the identity basis
as the best result, at 2,626 total ANF terms including the terminal function.
A 2,000-sample random GL(7,2) screen was substantially worse; its best score
was 45,283 terms. This rejects blind affine relabeling as the next optimization
lever. Evidence is in
`artifacts/destructive_semantic/reversible_width128_affine_relabel_screen.metrics.json`.

The order search was then rescored using the ANF complexity of every output
bit of every controlled state permutation, plus the terminal output function.
The best nearby order was
`q11,q9,q10,q5,q4,q2,q3,q1,q0,q8,q7,q6`, with 2,459 transition terms and 45
terminal terms (2,504 total). Its measured terminal tail is depth 1,967 /
1,109 CX. This is the best structured-transition score so far, although its
Gray-path MCT estimate is slightly worse than the previous order; it remains
an exact semantic control rather than a complete oracle. Measurements are in
`artifacts/destructive_semantic/reversible_width128_anf_order_search.metrics.json`.

The label allocator was strengthened to preserve branch multiplicity: a state
label reachable under both control values is preferred over one reachable under
only one value. A deterministic 200-seed tie-break screen on the ANF-best
order found a Pareto point at label seed 43: 1,540 Gray-path MCTs, 246
adjacent transpositions, and a terminal tail of depth 1,962 / 1,109 CX. This
is the current width-128 transition control; it still has no standalone
U3/CX classifier or exhaustive phase-oracle verification. Measurements are in
`artifacts/destructive_semantic/reversible_width128_label_seed_screen.metrics.json`.

One exact native pilot was then synthesized. For layer 6, branch 1 of the
seed-43 model, Gray-path routing produces 196 neighboring basis-state swaps.
Using six clean work qubits and Qiskit's exact `v-chain` MCX decomposition,
the standalone controlled transition compiles to depth 9,323 / 4,841 CX in
the required U3/CX basis with `qubits_initially_zero=False`. This is already
far beyond the complete-oracle target before the other five layers or the
terminal output are added. The reproducible pilot is
`src/reversible_transition_native_pilot.py`, with measurements in
`artifacts/destructive_semantic/reversible_transition_native_pilot.metrics.json`.
This establishes that the present arbitrary-permutation state-machine route
must be replaced by a more structured reversible update, not merely tuned by
more label seeds.

As a separate primitive test, repeated cubic destructive updates were applied
to the direct target wire of the residual-513 frontier. A four-layer, beam-4
search over all 3-control combinations stayed at residual 513; together with
the earlier exhaustive one-step cubic scan, this gives no evidence that cubic
target updates are the missing primitive. The compact result is in
`artifacts/destructive_semantic/cubic_direct_target_repeated.metrics.json`.

A broader degree scan found one five-control monomial that changes q11 and
improves the direct residual from 513 to 509:
`W[11] ^= W[0]W[2]W[7]W[8]W[14]`. Its exact U3/CX lowering, however, raises the
forward depth from 113 to 179 (140 CX), so the semantic improvement is not
competitive. This is recorded as a native rejection in
`artifacts/destructive_semantic/degree5_direct_target_control.metrics.json`.

## Clean-ancilla high-order correction

The shallow seed-42 candidate has a stronger opportunity than the direct-wire
frontier: its best affine combination is `q11 XOR q12`, and q17 is untouched
and therefore clean. The exact correction

```text
q17 ^= q2 & q3 & q4
q12 ^= q17 & q8 & q11
q17 ^= q2 & q3 & q4
```

uses three relative-phase 3-control X blocks. Semantic replay over all 4,096
inputs restores q17 and reduces the affine residual from 447 to 387. The
whole forward candidate compiles to depth 79 / 50 CX, which is a substantial
improvement over the previous 113-depth direct-wire candidate, although it is
still incomplete and has no exhaustive phase-oracle verification. The
reproducible builder is `src/high_order_affine_correction.py`; measurements
are in `artifacts/destructive_semantic/high_order_affine_correction.metrics.json`.

The clean workspace can be reused for a three-block chain. Adding the two
four-control corrections
`q12 ^= q7q8q10q11` and `q11 ^= q5q8q10q12` after the first five-control
correction reduces the affine residual further to 339. The exact semantic
chain restores q17 over all 4,096 inputs and compiles to forward depth 109 /
70 CX, crossing the promising depth screen while remaining incomplete. A
fourth correction lowers the residual to 323 but raises depth to 138, so the
three-block chain is the current depth/residual Pareto point. Its reproducible
builder is `src/high_order_affine_chain.py`; measurements are in
`artifacts/destructive_semantic/high_order_affine_chain.metrics.json`.

An all-degree monomial scan on the remaining `q11 XOR q12` residual found no
single exact completion. The best next correction is the previously measured
fourth block, reducing residual 339 to 323; a fifth six-control correction
reaches 315 but moves beyond the depth-screened construction. This boundary is
recorded in
`artifacts/destructive_semantic/high_order_affine_completion_scan.metrics.json`.

The depth-109 chain also exposed a second clean workspace: q13 is untouched by
the shallow base candidate. Using q17 for the first correction and q13 for the
second allows their compute and uncompute halves to overlap; only the two
toggles on q12 remain serial. The resulting exact semantic candidate keeps
residual 339, restores both clean ancillas over all 4,096 inputs, and compiles
to forward depth 98 / 72 CX. This is the current strongest depth-screened
candidate, still incomplete and not exhaustively verified as a phase oracle.
The builder and metrics are
`src/high_order_affine_parallel_chain.py` and
`artifacts/destructive_semantic/high_order_affine_parallel_chain.metrics.json`.

A v2 correction sequence replaces the first five-control block with the
four-control update `q12 ^= q2q3q4q11`. It preserves the same residual 339 and
depth 98, while reducing the compiled CX count from 72 to 66. Both q13 and
q17 remain clean and are restored. This is the current best depth/CX-screened
incomplete candidate; its builder and metrics are
`src/high_order_affine_parallel_chain_v2.py` and
`artifacts/destructive_semantic/high_order_affine_parallel_chain_v2.metrics.json`.

Finally, the remaining 339-point residual was passed to an exact bounded XAG
solver over 15 usable semantic signals. Zero, one, and two AND-node models
were proven unsatisfiable; the three-node model remained unknown after a
60-second bounded solve. Thus there is no confirmed low-AND completion yet.
The probe is recorded in
`artifacts/destructive_semantic/high_order_affine_xag_probe.metrics.json`.

## Reordered continuation

The next correction was tested in both orders. Applying
`q12 ^= q2q3q11q14` before `q11 ^= q5q8q10q12` reaches affine residual 323;
the reverse order reaches the same residual semantically, but the native
schedule is deeper. The reordered four-block chain uses q17 for the new
q12 correction and preserves q13 for the independent earlier correction.
It restores both clean ancillas over all 4,096 inputs and compiles to
forward depth 109 / 72 CX with `qubits_initially_zero=False` in the required
U3/CX basis. It is a promising incomplete classifier candidate, not a
verified phase oracle. The builder and metrics are
`src/high_order_affine_reordered_chain.py` and
`artifacts/destructive_semantic/high_order_affine_reordered_chain.metrics.json`.

A native-depth screen over direct `q11 XOR q12` residuals produced a tempting
107-depth / 76-CX pair using `q12 ^= q7q10q11q16`, then
`q11 ^= q8q10q12q16`. Independent exact affine-span replay rejected it: the
full residual is 339 rather than 323. This is retained only as a screening
lesson—direct target-combination residuals are insufficient, and every native
candidate must be checked with the full affine-span distance before it can
enter the frontier.

The residual-323 continuation was then rescheduled without changing its
semantics. In the tail, q17 computes `q2q3` and q13 computes `q8q10` before
either target toggle; q12 is toggled first, q11 second, and both workspaces
are then uncomputed. This preserves the dependency order while allowing the
independent partial products to overlap. Exact replay still restores q13 and
q17 over all 4,096 inputs and gives residual 323; required-basis transpilation
measures forward depth 102 / 72 CX. This is the current native-depth
frontier, still incomplete and not exhaustively verified as a phase oracle.
The builder and metrics are
`src/high_order_affine_fused_tail.py` and
`artifacts/destructive_semantic/high_order_affine_fused_tail.metrics.json`.

An exhaustive monomial continuation scan from residual 323 found no
improvement through five controls. A six-control update,
`q11 ^= q1q2q3q4q9q14`, lowers the exact affine residual to 315, but a
two-workspace relative-phase lowering compiles to depth 131 / 97 CX. It is
therefore a semantic improvement rejected by the native-depth objective; the
measurement is retained in
`artifacts/destructive_semantic/high_order_affine_six_control_probe.metrics.json`.
Reusing the q2q3 partial product across earlier q12 corrections was also
tested and remained depth 102 / 72 CX.

Additional residual-323 screens found no shorter continuation: all single
monomial updates through five controls, all ordered pairs of target-wire
RCCX updates, and all pairs of affine forms built from up to three current
wires failed to improve the residual. A deterministic sample of 300,000
three-affine-form products also found no improvement. These are semantic
pruning results, not a proof of optimality; the exact scopes and the one
six-control exception are recorded in
`artifacts/destructive_semantic/residual323_short_control_screens.metrics.json`.

The full one-step RCCX neighborhood was then checked with the exact affine
distance: all 2,448 choices of distinct control pair and physical target were
evaluated, including updates to garbage wires. None reduced residual 323.
This rules out a one-RCCX escape from the current state; the result is in
`artifacts/destructive_semantic/residual323_one_rccx_neighborhood.metrics.json`.

A bounded three-layer beam was then seeded from the fused residual-323 state
and allowed plain RCCX, restored one-sided affine-control, restored
two-sided affine-control, and forward two-sided affine-control updates. It
retained 64 states per layer, generated 265, 17,159, and 17,361 distinct
descendants, and exact-rescored 32 leaders at each layer. No exact leader
improved residual 323. This is a bounded negative result rather than an
optimality proof; its scope is recorded in
`artifacts/destructive_semantic/residual323_affine_beam.metrics.json`.

As a separate structural check, the repository's recursive 12-variable
formula decomposer was applied directly to the 1,097-state logo truth table.
It did not return a formula within a 20-second bounded probe, while the
preserved exact row-factor classifier is depth 6,531. This route is therefore
not competitive with the current destructive frontier; the bounded result is
recorded in
`artifacts/destructive_semantic/full12_formula_probe.metrics.json`.

Greedy ESOP analysis in the current-wire basis found two useful products:
`q11 ^= q1q2q3q4q9q14` lowers residual 323 to 315, followed by
`q12 ^= q2q3q4q7q8q10q11`, which lowers it to 307. The shared `q2q3q4`
factor can be computed once and reused, but the exact two-workspace lowering
still compiles to depth 160 / 117 CX. It is therefore a semantic insight and
native rejection, recorded in
`artifacts/destructive_semantic/residual323_greedy_esop.metrics.json`.

A comparison scan over the preserved double-RCCX bases found no better
starting basin for the native objective. The best alternative one-step
semantic result is residual 331 from a depth-107 base; the current fused
candidate remains depth 102 with residual 323. The representative basin
measurements are in
`artifacts/destructive_semantic/base_basin_correction_scan.metrics.json`.

Persistent linear basis changes were tested explicitly as two-step sequences.
CX→RCCX and RCCX→CX neighborhoods covered 590,944 and 749,088 nontrivial
sequences respectively; neither produced an affine-span proxy improvement
below 323. This closes the shallow persistent-CX escape around the current
state, but does not rule out deeper linear/nonlinear schedules. Measurements
are in
`artifacts/destructive_semantic/residual323_persistent_cx_screens.metrics.json`.
