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
threshold, but it is not a classifier: the target wire still mismatches 581
of 4,096 inputs, so no phase oracle was constructed or verified. Evidence is
in `artifacts/destructive_semantic/double_resume_b16x10_p4.metrics.json`.

The optional `--pareto-beam` selector now retains residual/depth
non-dominated states before filling the beam by the normal score. This is the
requested schedulability safeguard: a state can survive because it is
shallower even when its residual is slightly worse. On the beam-16,
double-RCCX layer-10 control it reproduced residual 581 and compiled depth 88,
with no improvement for seed 524. Evidence is in
`artifacts/destructive_semantic/double_pareto_b16x10_p4.metrics.json`.
