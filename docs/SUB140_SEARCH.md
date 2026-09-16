# Sub-140 search checkpoint

## Next architecture candidate: history-span phase synthesis

The attached deep-research assessment (see `POST185_DEEP_RESEARCH_REPORT.md`)
suggests a focused follow-up to the failed final-midpoint Direct-E searches.
At each reversible prefix, collect all 18 exact wire functions into a GF(2)
basis and test whether the logo target is represented by transient functions
with recoverable phase-tap locations. This may succeed even when the final
midpoint wires have a large nearest-affine residual. It is a proposed audit,
not a result; the protected 185/854/18 package remains unchanged.

Prioritize 7 nonlinear/18 affine and 8 nonlinear/12 affine trajectories, then
native-lower exact hits. Score native per-wire load and critical path alongside
semantic residual, and allow extra CX. Do not treat the symmetric RCCX ceiling
as a hard rejection rule for promising candidates, but reject any promotion
without exact standalone QASM verification and hash/package audit.

This file is a historical sub-140 checkpoint. The active target remains
**below 140**, followed by further depth reduction and rank one; the protected
full oracle is now **185 / 854 / 18**. None of the historical experiments
below produced a result below 196 or an official rank-one result.

## Boolean encoder searches

`post196_symmetric_encoder.py` requires three disjoint input products in the
first nonlinear layer and canonically orders their input groups. This removes
permutation copies inside a restricted two-layer model. Both 180-second runs
expired without a complete encoder. The y run reached 27 sampled inputs but
still had 96 full-domain class collisions; x reached 35 with 74 collisions.
These are rejected partial witnesses, not UNSAT conclusions.

`post196_class_constant_encoder.py` instead uses three nonlinear layers,
requires one code per class, and constrains all 64 input values immediately.
The extra nonlinear layer permits degree up to eight, avoiding the degree-four
ceiling of two layers. Its externally bounded outcomes are recorded separately.
A valid witness must also survive native lowering and all-64-input checks.

## New loader-free construction: six parallel quadratic features

Compute six disjoint pairwise ANDs into the six ancillas using relative-phase
Toffolis, apply a diagonal phase on coordinates and features, then apply the
actual inverse of the compute circuit. Relative phases cancel in this
compute/diagonal/uncompute arrangement. This is a different feature map from
the class-code loaders and permits phase synthesis across 18 wires.

On a two-input block, the available features `(a,b,a*b)` generate eight sign
characters on four input states. Invertible local sign bases yield an exact
real phase expansion. The searches allow coefficient changes by integer
multiples of pi, which change only global phase for a sign character, and
check the reconstructed phase on all 4096 inputs.

| Search | Completed work | Best result |
|---|---|---|
| Product of six four-state bases containing the constant | 100 restarts, adjacent/cross/random input pairings | 1,080 phase terms |
| Product bases also omitting the constant | 100 restarts | 1,085 terms |
| Coupled four-input bases, two ANDs per block | 12 restarts; greedy dyadic column exchanges among 64 local sign characters | **928 terms**, exact phase on all inputs |
| Coupled bases with signed ANF integer lifts | 20 restarts/polarities | 2,168 terms |
| Full implicit dictionary of 262,144 feature parities | 900 orthogonal-matching-pursuit steps using FWHT correlations | Not exact: max phase-function residual 0.09456 |

The 928-term result is a valid *phase representation*, not a native circuit.
Even allowing one constant term, its fixed representation needs at least
`ceil((3*927 - 2*18)/18) = 153` layers by gate occupancy, before accounting for
feature computation. It therefore cannot meet sub-140 through scheduling
alone, so an expensive native search was not started. This does not exclude
other equivalent phase representations with fewer terms. The matching-pursuit
approximation is rejected; it is not an oracle candidate.

Scripts: `post196_quadratic_tensor.py`, `post196_quadratic_tensor_full.py`,
`post196_quadratic_block_basis.py`, `post196_quadratic_block_lift.py`, and
`post196_quadratic_omp.py`. Their corresponding `artifacts/post196_*` folders
record settings, coefficients, residuals, and completed/bounded status.

## Conditional loading of the existing code bits

`post196_conditional_codes.py` computes a code bit, then uses its known value
as an additional control when expanding the next bit. This creates unreachable
addresses whose phase values need not be fixed. Reweighted L1 linear programs
search for sparse real expansions with exact equations on the 64 reachable
addresses. All six bit orders per side were screened; the two smallest-support
orders per side were compiled with four parity schedules per stage.

The reductions are real: one y bit drops to 15 terms when conditioned on an
earlier bit; the best x order uses 47, 21, 21 terms. However, sequential loading
loses the parallelism of the existing construction. Measured complete loaders:
**y 153/314 or 170/349; x 150/280 or 180/371** (depth/CX), all checked on 64
input mappings, worst error 7.04e-12. They are worse than the protected 77-layer
loaders and were not integrated into a full oracle.

## Validation and preservation

The implicit FWHT dictionary was checked against an explicit 64-column sign
matrix. A separate test reconstructs the saved 928-term representation and
checks the desired phase over all 4096 coordinates. Those tests and the
existing native-wire-identity regressions pass (four tests). The protected
196 QASM and original notebook have not been changed. No submission or
background automation was created.


The full-domain, three-layer class-constant searches on x and y both reached
their external 180-second limits without a witness. They remain UNKNOWN, not
UNSAT. Their CNFs have about 32,500 variables and 146,500 clauses each. No
partial solution was promoted to a native circuit.

A final coupled-basis variant used features `(a*b, a*b*c)` instead of two
pairwise products per four-input block. Twenty restarts produced a best exact
representation of 2,049 terms, worse than 928; see `post196_cubic_block_basis.py`
and `artifacts/post196_cubic_block`. No native candidate was warranted.

All bounded processes in this checkpoint have finished. No background search
or leaderboard monitor is scheduled. The sub-140 milestone is unresolved.
