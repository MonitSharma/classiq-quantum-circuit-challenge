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
