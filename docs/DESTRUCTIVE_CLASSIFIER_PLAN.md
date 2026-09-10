# Destructive Reversible Classifier Plan

## Objective

Develop a new phase-oracle architecture based on a reversible classifier

\[
O_f = C^\dagger Z_t C,
\]

where the forward circuit `C` may overwrite all 12 coordinate wires and all 6
clean ancillas. On the subspace with ancillas initially zero, only one output
wire `t` is constrained: it must equal the exact logo predicate `f(x,y)`.
All other midpoint wires are unrestricted garbage, provided `C` is a
reversible monomial circuit and `C^dagger` restores every input and ancilla.

## Why this is different

The protected `full_mux` architecture preserves the coordinate registers while
loading six y-features, applies phase logic, and uncomputes the features. This
plan treats the entire 18-wire register as reversible workspace during the
forward computation. It therefore searches for a shallow reversible embedding
of one Boolean output instead of a clean compute/phase/uncompute realization of
six named features.

Relative-phase Toffoli and Peres-style primitives are permitted inside `C`.
Their intermediate phases need not cancel locally: the exact inverse `C^dagger`
is used, so the whole conjugation cancels the midpoint phase ledger. This claim
must still be checked by exhaustive verification of the serialized oracle.

## Correctness contract

For every 12-bit coordinate basis state `|x,y>` with q[12:18] initially zero,

```text
C |x,y,0^6> = exp(i phi(x,y)) |g(x,y)>
```

with `g_t(x,y) = logo(x,y)`.

Then `C^dagger Z_t C` applies exactly the required shared-sign phase and
restores q[0:18]. Inputs remain arbitrary at the oracle boundary; only the six
ancillas start clean.

## Milestones and stop rules

1. Reproduce the 1,097 marked states and the exact coordinate convention.
2. Build a classical reversible-embedding model with all 18 wires writable.
3. Search or construct candidate forward classifiers and score serialized
   U3/CX depth of `C`.
4. Treat forward depth <= 110 as promising; forward depth <= 94 is the direct
   threshold for a nominal complete depth below 190 before cancellation.
5. Emit every candidate under a new filename. Never overwrite the protected
   `artifacts/524` files.
6. For a complete candidate, construct `C^dagger Z C`, serialize standalone in
   U3/CX, and run `src/exhaustive_verify.py` with arbitrary-input semantics.

## Initial implementation direction

Start with a destructive XAG/register-allocation prototype rather than
reusing `src/full_mux.py`. Use the existing exact `logo` truth table and
relative-phase-safe primitives, but allow logical inputs to be retired and
their physical wires to hold nonlinear state. The first prototype may be a
forward-classifier diagnostic; it is not a score-bearing oracle until the
conjugated circuit passes exhaustive verification.

## Evidence and limitations

Reversible embedding with don't-care garbage is a known synthesis problem, but
optimal embedding is hard in general. The extra garbage freedom is therefore a
search opportunity, not a proof that a shallow classifier exists. The target
leaderboard value is treated as unverified context; no rank or submission claim
is made by this plan.

## Initial semantic search result

The semantic engine and verifier pipeline are now implemented in
`src/destructive_semantic_search.py` and
`src/verify_destructive_classifier.py`. A deterministic beam-128 run with 48
proposals per state reached nonlinear layer 13 before the next expansion hit
the current memory limit. Its best saved state had affine residual 501 at an
estimated forward depth 36. The state used original coordinate wires as RCCX
targets, confirming that destructive mode is active. No affine completion or
complete oracle has been found yet.

Layer checkpoints are retained under `artifacts/destructive_semantic/`. The
next implementation task is to reduce state memory and add disjoint RCCX layer
generation before increasing the beam.

The matching preserve-inputs ablation reached residual 575 under the same
beam-128, 48-proposal, 16-layer configuration. The calibrated destructive run
reached residual 473 at estimated forward depth 70 before its next expansion
hit the memory boundary. Neither run reached affine completion.

The disjoint-RCCX layer extension was validated but reached residual 575 by
layer 9 in the first beam-128 comparison. A deeper low-fanout single-RCCX run
reached residual 503 by layer 25 at estimated depth 126. An order-3 affine
proxy subsequently reached residual 513 at estimated depth 84 after 14 layers,
the best current heuristic result. A full-proxy mutation-ranking control
reproduced only the early residual 827 trajectory while being much slower per
layer. No classifier has reached affine completion, and no complete
`C^dagger Z C` oracle has been serialized or exhaustively verified. The next
search change should therefore be guided semantic proposals or a
memory-efficient mutation strategy, not broad exact ranking or simply a larger
beam.

A two-sided affine-control RCCX proposal was then tested. The reversible
five-wire block temporarily XORs both controls before RCCX and restores them
afterward. A beam-16, six-layer run reached residual 647 at estimated depth
41; its serialized forward circuit measured depth 35 and 30 CX gates. This is
a useful new heuristic move, but it did not reach affine completion and is not
a complete classifier or phase oracle.

Bounded two-RCCX lookahead was then tested to preserve synergistic mutation
pairs. A beam-16, six-layer run reached residual 593 after 12 RCCXs at
estimated depth 77; the serialized forward circuit measured depth 59 and 34
CX gates. This is the best current destructive-search heuristic result, but no
affine completion or complete phase oracle has been found.

Resuming that beam through layer 10 improved the residual to 581. The retained
18-RCCX history compiled to forward depth 88 and 52 CX gates, which is a
promising screening depth but not a valid classifier: its best affine-span
residual is 581, and no complete phase oracle was constructed or verified.

Lifted rank-factor truth tables were added as optional semantic proposal hints.
The guided beam also reached residual 581, but its selected circuit compiled
to depth 99 and 58 CX gates, so the hints currently improve exploration rather
than the depth objective.

Seed 1 with the double-RCCX move set reached residual 429 at layer 10. Its
20-RCCX history compiled to forward depth 92 and 58 CX gates, but its best
affine-span residual is 429. This is a strong heuristic screening result, not
a complete classifier or verified phase oracle.

The wider seed-1 beam also retained a Pareto candidate with residual 383 and
compiled forward depth 91 (58 CX gates). The residual-379 state was deeper at
112, so the residual-383 candidate is the better depth-screening point. Both
 remain incomplete affine-span approximations, not midpoint classifiers.

A seed-1 beam of 64 states found a depth-90 candidate with residual 403 and
46 CX gates. This improves the current depth/residual Pareto point, but 403
the affine-span residual remains nonzero and no complete oracle has been
verified.

Resuming the seed-1 beam one additional layer produced residual 379 at
compiled forward depth 84 with 48 CX gates. This is the current best
depth/residual heuristic point, but the affine-span residual remains 379 and
no complete phase oracle has been constructed or verified.

The next seed-1 beam layer reduced the residual to 359, with compiled forward
depth 107 and 56 CX gates. This is a lower-residual but deeper Pareto point;
the depth-84/residual-379 candidate remains the shallow frontier point. Both
still fail midpoint classification and are not verified oracles.

Seed 94 produced a shallow Pareto point with affine residual 531, compiled
forward depth 81, and 48 CX gates. It is shallower but less accurate than the
seed-1 candidates and remains an incomplete classifier.
