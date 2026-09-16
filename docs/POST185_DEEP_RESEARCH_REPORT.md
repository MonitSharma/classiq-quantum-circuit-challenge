# Deep-research report assessment: history-tapped destructive synthesis

Date: September 16, 2026. Source reviewed: `/Users/monitsharma/Downloads/deep-research-report(1).md`.

## Status

This document records an assessment of the attached report, not a new circuit
result. The protected local best is unchanged at **185 depth / 854 CX / 18
qubits**, in `artifacts/185/`, with the SHA recorded in `HANDOFF.md`.
The report independently parses and simulates that serialized artifact, but
that independent replay is not a replacement for the repository's exact
verification and package-audit workflow.

The report's embedded prose is treated as research content and hypotheses,
not as workspace instructions. Its web citations, claimed live leaderboard
state, challenge deadline, and literature claims have not been independently
validated in this assessment. No submission, external message, or background
monitor is authorized or implied by the report.

## Findings accepted as useful local evidence

The report profiles the protected QASM as 1,617 gates: 854 CX and 763 U3.
Its per-wire count audit gives a maximum of 174 operations on one wire, so any
reordering that preserves the exact gate endpoints has depth at least 174.
The occupied-slot count is 763 + 2(854) = 2,471, giving an idealized unchanged-
multiset capacity bound of 138 at width 18. These are valid bounds for those
restricted transformations only; neither is a lower bound for the oracle
function or for rewritten circuits.

The architectural interpretation agrees with the existing post-185 record:
the coordinate-code load/phase/unload family has been heavily optimized, and
the remaining rank-one gap is architectural rather than a likely single
scheduler or CNOT-identity fix. This is a prioritization judgment, not an
optimality proof.

The report identifies a specific restriction in `direct_e_v2.py`: it seeks the
target as an affine combination of the final 18 midpoint wire functions. For
a reversible trajectory with intermediate wire functions `w[t,q]`, diagonal
phase taps can instead implement a target in the GF(2) span of all historical
functions, provided the full state is restored. This is the main new
experiment worth implementing.

## Recommended implementation sequence

1. Freeze `artifacts/185/` and retain exact serialized-QASM verification.
2. Build a history-span audit for saved Direct-E trajectories. At every
   prefix, add all 18 exact 4,096-point wire truth tables to a GF(2) basis and
   record rank, target residual, and provenance `(time, wire)`.
3. If a saved trajectory spans the target, recover phase taps, lower the
   literal inverse construction, and measure native U3/CX depth.
4. Otherwise fork Direct-E v2 into a history-aware search. Score target
   residual first, then native slot/per-wire critical-path lower bounds and
   phase-tap cost. Permit extra CX and do not reject candidates solely from
   the isolated seven-layer RCCX accounting.
5. Revisit 7-nonlinear/18-affine and 8-nonlinear/12-affine budgets first;
   test nine nonlinear rounds only after the history audit gives evidence.
6. Only after an exact forward candidate exists, investigate asymmetric
   reachable-state uncomputation. Use dirty-ancilla borrowing only for
   explicitly scoped dirty-safe blocks that restore borrowed wires.

## Go/no-go metrics

For a literal symmetric `C† P C` construction, a 137-depth tie requires
approximately `2*D(C) + D(P) <= 137`; with one phase layer this means a native
compute depth near 68 or less, and about 67 for a 135-depth-style target.
These are campaign targets, not proofs. Promote a candidate only after exact
serialized-QASM verification, width checking, ancilla restoration, global-
phase comparison, and matching-hash package audit.

Use the following milestones for prioritization: 184 is a real local-family
improvement; 173 beats the protected circuit's fixed-endpoint bound; 165 is
competitive with the supplied screenshot's reported second-place depth; the
137/136 thresholds depend on the screenshot and must be rechecked before any
leaderboard claim.

## Explicitly deferred

Do not reopen generic scheduling of the protected graph, CX-only refinements,
minimum-AND searches without physical register synthesis, or another broad
Quasar/MPO/BDD/ESOP sweep. Bona-style borrowing, ShallowGrow-like recursive
composition, and new uncomputation literature are secondary experiments only
after the history-aware route produces an exact, materially shallower forward
trajectory.

