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
- a cheap constant/single/pair residual heuristic;
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

The initial beam uses single RCCX transitions and a pairwise affine residual
proxy. It does not yet perform multi-RCCX disjoint layer generation, exact
meet-in-the-middle affine distance, guided rank/XAG seed pools, or a full
native-cost calibration. Disjoint layer generation and native-cost calibration
are now implemented; exact meet-in-the-middle distance is reported for the
selected final state but is not yet used to rank every child.

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
