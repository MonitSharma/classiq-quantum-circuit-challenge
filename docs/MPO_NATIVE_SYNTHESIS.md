# MPO-native synthesis campaign

For the cross-branch inventory of the preceding Boolean, reversible,
arithmetic, backend, and operator-native campaigns, see
[`METHOD_INDEX.md`](METHOD_INDEX.md). This file retains the detailed MPO
implementation and optimizer measurements.

## Status

This campaign is on branch `mpo-native-synthesis`. It optimizes the target
diagonal unitary directly rather than computing `logo(x,y)` into a classical
workspace. No submitted or verified competition circuit has been produced
yet. The protected `artifacts/524/full_mux_feature_linear_tket_524.qasm` file
is unchanged.

## Structural reproduction

The first milestone is implemented in `src/mpo_target.py`. It constructs the
sign tensor directly from `src/search.py::logo`, using the explicit tensor-axis
order

```text
q0, q1, q2, q3, q4, q5, q11, q8, q6, q7, q9, q10
```

The reproducible command is:

```sh
.venv/bin/python src/mpo_target.py
```

The current deterministic report is
`artifacts/mpo_native/structural_report.json`. It records:

| Quantity | Result |
|---|---:|
| Marked states | 1097 / 4096 |
| Sign-table SHA-256 | `9013c7bf82abcb1cbbcfff367b7321fb02c2a1cc1ba26ab2051640fd9b0eba13` |
| TT ranks, including endpoints | `[1, 2, 4, 8, 11, 12, 11, 12, 13, 8, 4, 2, 1]` |
| Maximum TT rank | 13 |
| Maximum TT reconstruction error | `2.01e-13` |
| Maximum diagonal-MPO basis-action error | `2.01e-13` |
| Ordinary sign-matrix rank across x\|y | 11 |

The decomposition is saved as `artifacts/mpo_native/target_tt.npz`; the
diagonal MPO cores are saved separately as
`artifacts/mpo_native/target_mpo.npz`. The sign table is saved as
`artifacts/mpo_native/target_signs.npy`.

The TT ranks are numerical ranks from double-precision SVD with a relative
cutoff of `1e-12`. Reconstruction is checked over every tensor entry, and the
MPO action is checked over every 12-bit basis string. This establishes the
claimed tensor structure, but it does not establish a shallow circuit: MPO
bond dimension is not a depth bound, and TT cores are not automatically
unitary or isometric.

The same report includes two comparison orders. The natural challenge order
has maximum TT rank 17, and the reverse order also has maximum rank 17. Thus
the rank-13 result is not a generic artifact of the tensor dimensions; the
interleaved order is materially better for this target.

## Planned synthesis experiments

The next bounded experiment should optimize a full-operator objective for
12-qubit circuits with no ancillas. Candidate circuits must be evaluated as
operators, not by state fidelity or diagonal entries alone. The process
fidelity target is

```text
|Tr(U_target† V)|² / 4096²
```

The initial topology ladder should include TT-order matchings, all-to-all
round-robin matchings, and explicit x-y matchings at 4, 6, 8, 10, 12, 16,
20, and 24 parallel two-qubit layers. Every promising result must eventually
be decomposed to exact `u3`/`cx` QASM and checked with the repository's
exhaustive verifier and dense random-state verifier. No abstract SU(4) depth
or optimizer loss will be treated as a competition result.

The optimizer must also preserve arbitrary input states. Any future use of
Qiskit transpilation for reusable circuit pieces must pass
`qubits_initially_zero=False`, consistent with the repository-wide correctness
rule.

`src/mpo_contract.py` provides an exact local MPO application and
Hilbert--Schmidt contraction for adjacent TT-order gates. Its cross-check is
`src/mpo_contract_smoke.py`; the recorded result in
`artifacts/mpo_native/contraction_smoke.json` agrees with dense Qiskit output
to `1.48e-22` absolute process-fidelity difference for a random six-gate
layer. This validates the tensor index convention and provides the future
optimizer with a non-dense objective path.

The pinned Riemannian smoke wrapper is `src/mpo_rqcopt_smoke.py`. It now uses a
phase-invariant process loss based on `|Tr(U_target^dagger V)|`, with the
phase-aligned gradient projected onto each SU(4) tangent space. A bounded
100-iteration, 2-layer, near-identity run improved process fidelity from
`0.1407954265` to `0.2944914418`. A warm-started 4-layer run improved from
`0.2944914418` to `0.3019871592` in 50 iterations. These are feasibility
signals only, not candidates: they use abstract two-qubit gates and have not
been decomposed or exhaustively verified as challenge QASM. Identity
initialization is stationary for the first-order objective at this target, so
near-identity or random restarts are necessary. Run records append to
`artifacts/mpo_native/progress.jsonl`.

The 4-layer/50-iteration warm checkpoint compiles to a 12-qubit diagnostic
QASM circuit at **depth 25 / 64 CX** (`artifacts/mpo_native/rqcopt_phase_4x50_warm_compiled.qasm`, SHA
`551c977d3bc7423456abde4f0c01d884239e586e325f9a7a29545436e3e91e0a`). Its
abstract process fidelity is `0.3019871592`; it is explicitly not promoted,
because approximate process fidelity is not the challenge's exact oracle
criterion. Replaying the serialized QASM through the MPO contraction gives
`0.3019871591263913`, an absolute difference of about `6.7e-11` from the
abstract checkpoint. Exact challenge verification remains pending.

A 6-layer warm start from that 4-layer checkpoint reached `0.3019961070` in
20 iterations, effectively a plateau. This is an early warning that simply
adding identity-initialized layers is not sufficient; the next useful run
should vary topology, restart phase, or optimize the native decomposed
topology rather than blindly increasing layer count.

A reduced-step 100-iteration continuation of the 4-layer checkpoint reached
only `0.3020024344`, confirming that the earlier 0.302 plateau is not chiefly
an insufficient iteration count.

An 8-layer warm-start probe was also negative: after 10 iterations it reached
`0.3019521264`, slightly below the 4-layer checkpoint, with the added identity
layers introducing phase drift. The current adjacent-chain/RieADAM family is
therefore closed for now; further effort should change the interaction
topology or optimizer parameterization rather than extend this ladder.

As a bounded order control, 2-layer near-identity runs for 50 iterations
reached process fidelities `0.2177549926` in natural challenge order and
`0.2233680863` in reverse order, versus the interleaved TT-order campaign's
much stronger 4-layer result. This supports retaining the interleaved order as
the current chain topology, while leaving all-to-all matching topologies as
the next major structural experiment.

An explicit alternating x-y order `(x0,y0,x1,y1,...,x5,y5)` was also tested
for 2 layers and 50 iterations. It reached `0.2189523424`, only modestly above
the identity baseline. Its exact TT maximum rank is 26, versus 13 for the
interleaved order, so this first cross-register chain is not competitive. It
does not rule out a genuinely non-chain all-to-all matching circuit.

A reproducible 100-sample permutation screen is implemented in
`src/search_mpo_orders.py`. With seed `20260911`, the best sampled order was
the existing interleaved order at maximum TT rank 13; every random order was
at least 22. This is not an exhaustive ordering proof, but it removes the
most immediate possibility that a simple relabeling gives a better chain
ansatz.

The true non-chain evaluation primitive is now implemented in
`src/mpo_contract.py::apply_nonadjacent_gate`. It contracts the full MPO
window between two sites and re-splits it exactly, without adding SWAP gates.
`src/mpo_nonadjacent_smoke.py` validates a six-gate long-range round-robin
matching against dense Qiskit: process fidelities agree to `4.0e-21`. This is
an evaluation foundation for the next all-to-all optimizer; it is not yet an
optimized candidate.

## External optimizer assessment

The public `INMLe/rqcopt-mpo` repository is relevant: its brick-wall routines
take a reference MPO and compute full operator overlaps and Riemannian
gradients for local unitary gates. It is not merely a state-preparation
library. However, the supplied implementation is organized around JAX,
one-dimensional/swap-network layouts, and its model-specific configuration
layer. JAX/JAXLIB `0.4.38` is now installed in the existing `.venv` solely for
this bounded adapter; it is not a new environment or an unmodified upstream
long-running campaign. The upstream README and implementation are pinned and
adapted only through local target-objective smoke tests.

The source is locally inspected under `external/rqcopt-mpo/` at commit
`95f0898f7baa6579de512eba8b00386bd6b05217`. It remains ignored from the main
repository history; the commit pin is recorded here for reproducibility.

The immediate local topology support is in `src/mpo_topologies.py`. It emits
disjoint all-to-all matchings and TT-order brick-wall layers without inserting
physical SWAPs. This separates topology generation from the eventual choice
of optimizer.

## Operator-objective smoke test

`src/mpo_objective.py` provides an exact dense diagnostic for small bounded
experiments. Run it with:

```sh
.venv/bin/python src/mpo_objective.py
```

The current smoke output is in
`artifacts/mpo_native/objective_smoke.jsonl`. Identity has process fidelity
`0.21562600135803223`, exactly matching the squared normalized trace of the
sign target. A random six-gate matching layer has process fidelity about
`5.84e-9` and normalized off-diagonal Frobenius leakage about `0.99987`.
This confirms that the objective is measuring the full operator rather than
only diagonal agreement. The dense path is deliberately not the eventual
training loop; it is the correctness oracle for later MPO contractions.

## Non-chain optimizer capability result

The exact arbitrary-pair primitive was validated independently: a six-gate
long-range round-robin matching agrees with dense evaluation to about
`4.0e-21` in process-fidelity comparison. Directly differentiating through
the MPO re-factorization was then tested, but the installed JAX path is not a
stable optimizer substrate: QR derivatives are unimplemented and exact SVD
derivatives encounter the repeated-singular-value gauge of unitary matching
layers.

As a bounded capability test, `src/mpo_nonchain_optimizer.py` now optimizes
the exact process-overlap contribution of one disjoint matching using JAX
autodiff, without a state-only surrogate or finite-difference gradients. The
20-step run improved fidelity from `0.1724585425` to `0.1748858031`; a
200-step run reached `0.1917240554`. These are not complete-oracle results:
the objective is exact for the one-layer disjoint matching, but the ansatz is
far too small to represent the target. The result demonstrates stable
nonlocal gate-gradient plumbing, not a competitive construction.

The next meaningful MPO experiment therefore needs a differentiable
multi-layer tensor-network parameterization that avoids differentiating an
SVD/QR gauge at every gate application, or an equivalent operator-level
optimizer with a fixed bond-coordinate representation. The validated
non-adjacent contraction remains available for post-optimization checking.

## Gatewise Procrustes sweep

`src/mpo_gate_sweep.py` implements the required second optimizer strategy.
For a selected two-qubit gate it contracts the exact target/circuit tensor
network with each of the 16 matrix-unit gates, producing the linear local
environment. An SVD/polar update then maximizes the local process overlap,
with a determinant-one gauge. It uses no finite-difference gradients and does
not form a dense candidate unitary at every update. Contraction paths are
cached by tensor-network shape.

The identity-control check gives overlap `1902` and process fidelity
`0.215626001358`, matching the independent dense objective. A local update
was also checked directly: the exact overlap magnitude increased for both
layers of a random two-layer circuit.

The bounded logo ladder is:

| topology | layers | SU(4) gates | init/seed | final process fidelity | native depth / CX | status |
|---|---:|---:|---|---:|---:|---|
| round-robin | 2 | 12 | near-identity/20260911 | 0.3554331 | not separately compiled | approximate |
| round-robin | 2 | 12 | Haar/1 | 0.3551808 | — | approximate |
| round-robin | 2 | 12 | Haar/2 | 0.3553914 | — | approximate |
| round-robin | 4 | 24 | near-identity/20260911 | 0.3589812 | **17 / 48** | approximate |
| round-robin | 6 | 36 | near-identity/20260911 | 0.3698519 | **25 / 72** | approximate |
| TT brickwall | 4 | 22 | near-identity/20260911 | 0.3003704 | — | approximate |
| TT brickwall | 4 | 22 | Haar/1 | 0.3049445 | — | approximate |
| TT brickwall | 6 | 33 | near-identity/20260911 | 0.3015227 | **37 / 99** | approximate |
| x-y | 4 | 24 | near-identity/20260911 | 0.2823249 | — | approximate |

The round-robin 4-layer QASM was independently loaded as a 4096-dimensional
operator; its diagonal process fidelity was `0.3589811799023`, agreeing with
the abstract tensor objective to about `1.2e-14`. It is not a candidate for
promotion because its process error is enormous. The six-layer run required
about 818 seconds for five exact sweeps and still had process infidelity
`0.6301481`; it is a useful bounded datapoint, not a candidate. The
eight-layer round-robin contraction was stopped after several minutes when
its exact nonlocal path became impractical and produced no result. The
completed TT ladder plateaus near
0.30, and the tested x-y family is weaker. Blindly increasing these fixed
topologies is therefore not justified.

The compiler helper `src/compile_mpo_sweep.py` preserves arbitrary-input
semantics with `qubits_initially_zero=False`, emits standalone `u3/cx` QASM,
and writes compile metrics to a separate `.compile.json` file so optimizer
checkpoints cannot be overwritten.

The matching sequence is now an explicit parameter rather than an implicit
first-`L` choice. Three deterministic four-layer screens gave fidelities
`0.3589812` for `[0,1,2,3]`, `0.3555679` for `[0,2,4,6]`, and `0.3553529`
for `[0,3,6,9]`. A fourth sparse sequence `[0,5,7,10]` was stopped after
more than a minute in its exact environment contraction and produced no
result. This small adaptive-topology screen found no escape from the
round-robin plateau; it also shows that arbitrary-pair environment cost can
become the limiting factor before fidelity does.

## Four-ancilla bus diagnostic

The deferred bond-memory experiment is implemented in
`src/mpo_bus_sweep.py`. It uses four clean ancillas, sequential SU(4) gates
between bus and data wires, and explicit `|0000>` boundary vectors on both
ends. Consequently the objective is the clean-subspace process overlap and
ancilla leakage is automatically penalized. This is an optimization ansatz,
not an assumption that TT cores are unitary.

| bus interactions per data | SU(4) gates | init/seed | sweeps | clean-subspace fidelity |
|---:|---:|---|---:|---:|
| 1 | 12 | identity | 1 | 0.2156260 |
| 2 | 24 | Haar/1 | 10 | 0.2597197 |
| 4 | 48 | Haar/1 | 15 | 0.2656592 |

The bus family is below the best no-ancilla matching result (`0.3589812`),
and its convergence is visibly slow. Stop this exact schedule family rather
than expanding it blindly; a future bus attempt would need a different
multi-pass/isometric parameterization.

## Promotion gate

`src/promote_mpo_candidate.py` is the only path that can label an MPO QASM
artifact promoted. It checks the serialized file's SHA, standalone `u3/cx`
basis, and width, then delegates to `src/exhaustive_verify.py`. Running it on
the 4-layer round-robin checkpoint correctly rejected the approximate circuit
(`max_error` about `2.0`, with a discarded-amplitude bound below `4e-13`),
despite its depth 17 / 48 CX metrics. No MPO artifact is verified or promoted.

## Sequential-memory and Riemannian controls

The more permissive sequential-memory ansatz in
`src/mpo_sequential_unitary.py` gives each of the 12 data sites an arbitrary
32x32 unitary on a 16-dimensional memory plus the data qubit. Its exact
left/right TT environments are inexpensive and the gatewise polar update is
stable. Twenty deterministic Haar restarts (15 sweeps each) converged to
`0.2661164`–`0.2661561`; natural and reverse controls reached only
`0.2604468` and `0.2604443`. Increasing memory dimension to 32 and 64 did not
change the plateau (`0.2661013` and `0.2658465`). This closes the simple
single-pass sequential-unitary architecture more strongly than the earlier
SU(4)-bus test.

`src/mpo_rie_state.py` also provides the requested Riemannian fixed-topology
control using a batched Rademacher estimator of the full operator trace. A
64-probe, 300-step four-layer round-robin run moved only from about `0.08283`
to `0.08293` before drifting down to `0.08227`; it did not outperform exact
gatewise sweeps. Its estimates are diagnostic only and are never accepted by
the promotion pipeline.

The executable invariant suite is `tests/test_mpo_native.py`; the current
run is six tests passing. It covers target counts/ranks, TT/MPO reconstruction,
global-phase-invariant process metrics, exact local sweep improvement, QASM
angle round-trip, and promotion preconditions.

## Analytic Adam depth ladder

`src/mpo_adam_su4.py` parameterizes every SU(4) gate as an exponential of 15
traceless Pauli products and optimizes with JAX autodiff/Adam. The fixed
round-robin cycle showed a real but slow trend under 64-probe trace estimates:

| SU(4) layers | estimated fidelity | exact fidelity check | native depth / CX |
|---:|---:|---:|---:|
| 8 | 0.4003 | — | — |
| 10 | 0.4368 | — | — |
| 12 | 0.4565 | — | — |
| 16 | 0.5080 | — | — |
| 20 | 0.5408 | — | — |
| 24 | 0.5718 | **0.5690** | — |
| 32, warm from 24 | 0.6454 | **0.6434** | — |
| 40, warm from 32 | 0.6645 | **0.6616** | **241 / 720** |

The exact checks use all 4096 computational-basis inputs, not the stochastic
training estimate. A random 24-layer matching order reached only 0.5480,
below the regular round-robin cycle. The 40-layer circuit is already deeper
than the working leaderboard target before correctness is approached, so this
fixed matching/Adam family is closed for the competition objective.

An analytic bus control, `src/mpo_adam_bus.py`, was tested separately. It
optimizes 48 SU(4) data/memory interactions with a clean-ancilla process-trace
estimator. With 64 fixed Rademacher probes and 150 Adam steps it reached only
estimated fidelity `0.3734214`, below the no-ancilla 24-layer result. The
earlier 8-probe run reached `0.3765` but was not treated as reliable evidence;
the higher-probe control confirms that this bus schedule is not competitive.
