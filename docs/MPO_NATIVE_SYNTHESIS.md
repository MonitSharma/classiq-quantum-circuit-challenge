# MPO-native synthesis campaign

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

The pinned Riemannian smoke wrapper is `src/mpo_rqcopt_smoke.py`. A bounded
20-iteration, 2-layer, near-identity run improved process fidelity from
`0.1407954265` to `0.1567285921`. This is a feasibility signal only, not a
candidate: it is still below the identity baseline `0.2156260014`, uses an
abstract two-qubit-gate topology, and has not been decomposed or exhaustively
verified as challenge QASM. Identity initialization is stationary for the
real-overlap objective at this target, so near-identity or random restarts are
necessary. Run records append to `artifacts/mpo_native/progress.jsonl`.

## External optimizer assessment

The public `INMLe/rqcopt-mpo` repository is relevant: its brick-wall routines
take a reference MPO and compute full operator overlaps and Riemannian
gradients for local unitary gates. It is not merely a state-preparation
library. However, the supplied implementation is organized around JAX,
one-dimensional/swap-network layouts, and its model-specific configuration
layer. The current repository environment does not have JAX installed, so it
has not been added as an implicit dependency or launched as a long-running
experiment. The upstream README and implementation should be pinned and
adapted only after a local target-objective smoke test.

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
